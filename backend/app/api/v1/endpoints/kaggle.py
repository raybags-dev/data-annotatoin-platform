"""Kaggle dataset search, download, and ingest endpoints.

Flow:
  GET  /kaggle/search?q=...     → list datasets from Kaggle
  POST /kaggle/download         → {handle} → downloads + unzips to /tmp, returns file list
  POST /kaggle/ingest           → {download_id, filename, name} → uploads chosen CSV to
                                  Supabase bucket and creates ann_datasets record
"""
from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import AsyncClient

from app.core.config import settings
from app.core.database import get_db
from app.core.storage import upload_raw
from app.repositories.dataset_repo import DatasetRepository

router = APIRouter()

# ── session store: download_id → (tmp_dir_path, created_at) ────────────────
_sessions: dict[str, tuple[str, datetime]] = {}
_SESSION_TTL = timedelta(minutes=30)


def _purge_stale() -> None:
    now = datetime.utcnow()
    stale = [k for k, (_, t) in _sessions.items() if now - t > _SESSION_TTL]
    for k in stale:
        path, _ = _sessions.pop(k)
        shutil.rmtree(path, ignore_errors=True)


def _auth_kaggle():
    """Set env vars and authenticate the kaggle API client."""
    if not settings.KAGGLE_USERNAME or not settings.KAGGLE_KEY:
        raise HTTPException(
            503,
            "Kaggle credentials not configured — set KAGGLE_USERNAME and KAGGLE_KEY in .env",
        )
    os.environ["KAGGLE_USERNAME"] = settings.KAGGLE_USERNAME
    os.environ["KAGGLE_KEY"] = settings.KAGGLE_KEY
    import kaggle  # local import — keeps startup fast when not configured
    kaggle.api.authenticate()
    return kaggle


def _repo(db: AsyncClient = Depends(get_db)) -> DatasetRepository:
    return DatasetRepository(db)


# ── schemas ─────────────────────────────────────────────────────────────────

class DownloadRequest(BaseModel):
    handle: str  # "owner/dataset-slug"


class IngestRequest(BaseModel):
    download_id: str
    filename: str   # relative path inside the extracted archive
    name: str = "" # optional display name; defaults to filename stem


# ── endpoints ───────────────────────────────────────────────────────────────

@router.get("/search")
async def search_kaggle(q: str, page_size: int = 12):
    """Search public Kaggle datasets. Returns up to page_size results."""
    _purge_stale()
    try:
        kg = _auth_kaggle()
        results = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: kg.api.dataset_list(search=q, page=1, page_size=page_size),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Kaggle API error: {exc}") from exc

    return [
        {
            "ref": getattr(r, "ref", str(r)),
            "title": getattr(r, "title", ""),
            "subtitle": getattr(r, "subtitle", None),
            "size": getattr(r, "totalBytes", None),
            "last_updated": str(getattr(r, "lastUpdated", "")),
            "download_count": getattr(r, "downloadCount", 0),
            "vote_count": getattr(r, "voteCount", 0),
            "url": f"https://www.kaggle.com/datasets/{getattr(r, 'ref', '')}",
        }
        for r in results
    ]


@router.post("/download")
async def download_kaggle_dataset(body: DownloadRequest):
    """Download and unzip a Kaggle dataset. Returns list of usable files."""
    _purge_stale()
    kg = _auth_kaggle()

    tmp_dir = tempfile.mkdtemp(prefix="kaggle_")
    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: kg.api.dataset_download_files(
                body.handle, path=tmp_dir, unzip=True, quiet=True
            ),
        )
    except Exception as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(502, f"Kaggle download failed: {exc}") from exc

    files: list[dict] = []
    for pattern in ("*.csv", "*.json", "*.xlsx", "*.xls"):
        for f in sorted(Path(tmp_dir).rglob(pattern)):
            files.append(
                {
                    "filename": str(f.relative_to(tmp_dir)),
                    "size": f.stat().st_size,
                    "type": f.suffix.lower().lstrip("."),
                }
            )

    if not files:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(
            404, "No supported files (CSV / JSON / Excel) found in dataset"
        )

    download_id = str(uuid.uuid4())
    _sessions[download_id] = (tmp_dir, datetime.utcnow())
    return {"download_id": download_id, "handle": body.handle, "files": files}


@router.post("/ingest")
async def ingest_kaggle_file(
    body: IngestRequest,
    repo: DatasetRepository = Depends(_repo),
):
    """Upload chosen file to Supabase and register it as a dataset."""
    session = _sessions.get(body.download_id)
    if not session:
        raise HTTPException(
            404, "Download session expired or not found — search and download again"
        )
    tmp_dir, _ = session
    filepath = Path(tmp_dir) / body.filename
    if not filepath.exists():
        raise HTTPException(404, f"File not found in downloaded archive: {body.filename}")

    data = await asyncio.get_event_loop().run_in_executor(None, filepath.read_bytes)

    ext = filepath.suffix.lower().lstrip(".")
    file_type = {"csv": "csv", "json": "json", "xlsx": "excel", "xls": "excel"}.get(ext, "txt")
    content_type = {
        "csv": "text/csv",
        "json": "application/json",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }.get(ext, "application/octet-stream")

    storage_path = f"datasets/{uuid.uuid4()}/{filepath.name}"
    try:
        url = await asyncio.get_event_loop().run_in_executor(
            None, lambda: upload_raw(storage_path, data, content_type)
        )
    except RuntimeError:
        url = ""

    doc = {
        "name": body.name.strip() or filepath.stem,
        "filename": filepath.name,
        "file_type": file_type,
        "storage_path": storage_path,
        "storage_url": url,
        "status": "uploaded",
        "row_count": 0,
        "column_count": 0,
        "columns": [],
        "validation_report": None,
        "cleaning_report": None,
        "labeling_config": {"categories": [], "model": settings.OLLAMA_MODEL},
        "processing_history": [],
    }
    dataset_id = await repo.create(doc)

    # Clean up session and temp directory
    _sessions.pop(body.download_id, None)
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: shutil.rmtree(tmp_dir, ignore_errors=True)
    )

    return {"id": dataset_id, **doc}
