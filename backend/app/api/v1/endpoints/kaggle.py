"""Kaggle dataset search, async download, and ingest endpoints.

Flow:
  GET  /kaggle/search                         → list datasets from Kaggle
  POST /kaggle/download                       → {handle, size_bytes?} → starts background
                                                download, returns download_id immediately
  GET  /kaggle/download-status/{download_id}  → poll until status == "ready" or "error"
  POST /kaggle/ingest                         → {download_id, filename, name} → uploads chosen
                                                CSV to Supabase bucket and creates ann_datasets
"""
from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import AsyncClient

from app.core.config import settings
from app.core.database import get_db
from app.core.storage import upload_raw
from app.repositories.dataset_repo import DatasetRepository

router = APIRouter()

# ── session store ────────────────────────────────────────────────────────────
# download_id → session dict
_sessions: dict[str, dict[str, Any]] = {}
_SESSION_TTL = timedelta(minutes=30)


def _purge_stale() -> None:
    now = datetime.utcnow()
    stale = [k for k, v in _sessions.items() if now - v["created_at"] > _SESSION_TTL]
    for k in stale:
        sess = _sessions.pop(k)
        if sess.get("tmp_dir"):
            shutil.rmtree(sess["tmp_dir"], ignore_errors=True)


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


# ── background download task ─────────────────────────────────────────────────

async def _do_download(download_id: str, handle: str) -> None:
    """Background task: download the Kaggle dataset and update the session."""
    session = _sessions.get(download_id)
    if session is None:
        return

    tmp_dir = tempfile.mkdtemp(prefix="kaggle_")
    session["tmp_dir"] = tmp_dir

    try:
        kg = _auth_kaggle()
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: kg.api.dataset_download_files(
                handle, path=tmp_dir, unzip=True, quiet=True
            ),
        )
    except Exception as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        session["tmp_dir"] = None
        session["status"] = "error"
        session["error"] = f"Kaggle download failed: {exc}"
        return

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
        session["tmp_dir"] = None
        session["status"] = "error"
        session["error"] = "No supported files (CSV / JSON / Excel) found in dataset"
        return

    session["files"] = files
    session["status"] = "ready"


# ── schemas ──────────────────────────────────────────────────────────────────

class DownloadRequest(BaseModel):
    handle: str            # "owner/dataset-slug"
    size_bytes: int | None = None  # total size from Kaggle search result


class IngestRequest(BaseModel):
    download_id: str
    filename: str    # relative path inside the extracted archive
    name: str = ""   # optional display name; defaults to filename stem


# ── endpoints ────────────────────────────────────────────────────────────────

@router.get("/search")
async def search_kaggle(q: str):
    """Search public Kaggle datasets."""
    _purge_stale()
    try:
        kg = _auth_kaggle()
        results = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: kg.api.dataset_list(search=q, page=1),
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
async def download_kaggle_dataset(
    body: DownloadRequest,
    db: AsyncClient = Depends(get_db),
):
    """Start an async Kaggle download. Returns download_id for status polling."""
    _purge_stale()

    # Size guard — reject if the caller already knows the size exceeds the limit
    if body.size_bytes is not None and body.size_bytes > settings.MAX_DATASET_BYTES:
        raise HTTPException(
            400,
            f"Dataset is {body.size_bytes / 1024 / 1024:.1f} MB, "
            f"which exceeds the {settings.MAX_DATASET_BYTES // 1024 // 1024} MB limit.",
        )

    # Duplicate check — if already imported, return the existing record
    repo = DatasetRepository(db)
    existing = await db.table("ann_datasets").select("id").eq("kaggle_handle", body.handle).limit(1).execute()
    if existing.data:
        return {"existing": True, "dataset_id": existing.data[0]["id"]}

    # Create session and fire background task
    download_id = str(uuid.uuid4())
    _sessions[download_id] = {
        "status": "pending",
        "handle": body.handle,
        "tmp_dir": None,
        "files": None,
        "error": None,
        "created_at": datetime.utcnow(),
        "size_bytes": body.size_bytes,
    }

    asyncio.create_task(_do_download(download_id, body.handle))

    return {"download_id": download_id, "status": "pending", "handle": body.handle}


@router.get("/download-status/{download_id}")
async def get_download_status(download_id: str):
    """Poll the status of an ongoing or completed download."""
    session = _sessions.get(download_id)
    if not session:
        raise HTTPException(404, "Download session not found or expired")

    # Return the session dict without the tmp_dir path (internal detail)
    return {
        "status": session["status"],
        "handle": session["handle"],
        "files": session.get("files"),
        "error": session.get("error"),
    }


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
    if session["status"] != "ready":
        raise HTTPException(400, f"Download is not ready yet (status: {session['status']})")

    tmp_dir = session["tmp_dir"]
    filepath = Path(tmp_dir) / body.filename
    if not filepath.exists():
        raise HTTPException(404, f"File not found in downloaded archive: {body.filename}")

    data = await asyncio.get_event_loop().run_in_executor(None, filepath.read_bytes)
    file_size_bytes = len(data)

    # Backend size double-check
    if file_size_bytes > settings.MAX_DATASET_BYTES:
        raise HTTPException(
            400,
            f"File is {file_size_bytes / 1024 / 1024:.1f} MB, "
            f"which exceeds the {settings.MAX_DATASET_BYTES // 1024 // 1024} MB limit.",
        )

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

    handle = session.get("handle", "")

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
        "file_size_bytes": file_size_bytes,
        "kaggle_handle": handle,
    }
    dataset_id = await repo.create(doc)

    # Clean up session and temp directory
    _sessions.pop(body.download_id, None)
    await asyncio.get_event_loop().run_in_executor(
        None, lambda: shutil.rmtree(tmp_dir, ignore_errors=True)
    )

    return {"id": dataset_id, **doc}
