from __future__ import annotations
import asyncio
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from supabase import AsyncClient
from app.core.database import get_db
from app.core.storage import upload_raw, delete_raw
from app.repositories.dataset_repo import DatasetRepository
from app.models.dataset import LabelingConfig

router = APIRouter()

def _repo(db: AsyncClient = Depends(get_db)) -> DatasetRepository:
    return DatasetRepository(db)

@router.get("")
async def list_datasets(repo: DatasetRepository = Depends(_repo)):
    return await repo.list_all()

# NOTE: /storage-summary must be registered BEFORE /{dataset_id} so FastAPI
# does not match the literal string "storage-summary" as a dataset_id.
@router.get("/storage-summary")
async def storage_summary(db: AsyncClient = Depends(get_db)):
    """Return total file_size_bytes and dataset count across all datasets."""
    res = await db.table("ann_datasets").select("file_size_bytes").execute()
    rows = res.data or []
    total_bytes = sum(r.get("file_size_bytes") or 0 for r in rows)
    return {"total_bytes": total_bytes, "dataset_count": len(rows)}

@router.get("/{dataset_id}/preview")
async def preview_dataset(dataset_id: str, db: AsyncClient = Depends(get_db)):
    """Return first 20 rows of ann_records for a dataset."""
    res = (
        await db.table("ann_records")
        .select("raw_data")
        .eq("dataset_id", dataset_id)
        .order("row_index")
        .limit(20)
        .execute()
    )
    rows_data = [r["raw_data"] for r in (res.data or [])]
    columns: list[str] = []
    if rows_data:
        columns = list(rows_data[0].keys())
    return {"columns": columns, "rows": rows_data}

@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str, repo: DatasetRepository = Depends(_repo)):
    doc = await repo.get(dataset_id)
    if not doc:
        raise HTTPException(404, "Dataset not found")
    return doc

@router.post("")
async def upload_dataset(
    name: str = Form(...),
    file: UploadFile = File(...),
    repo: DatasetRepository = Depends(_repo),
):
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else "txt"
    file_type = {"csv": "csv", "json": "json", "xlsx": "excel", "xls": "excel", "txt": "txt"}.get(ext, "txt")
    data = await file.read()
    file_size_bytes = len(data)
    path = f"datasets/{uuid.uuid4()}/{file.filename}"
    try:
        url = upload_raw(path, data, file.content_type or "application/octet-stream")
    except RuntimeError:
        url = ""

    doc = {
        "name": name,
        "filename": file.filename,
        "file_type": file_type,
        "storage_path": path,
        "storage_url": url,
        "status": "uploaded",
        "row_count": 0,
        "column_count": 0,
        "columns": [],
        "validation_report": None,
        "cleaning_report": None,
        "labeling_config": {"categories": [], "model": "llama3.2:3b"},
        "processing_history": [],
        "file_size_bytes": file_size_bytes,
        "kaggle_handle": "",
    }
    dataset_id = await repo.create(doc)
    return {"id": dataset_id, **doc}

@router.put("/{dataset_id}/labeling-config")
async def set_labeling_config(
    dataset_id: str,
    config: LabelingConfig,
    repo: DatasetRepository = Depends(_repo),
):
    await repo.update(dataset_id, {"labeling_config": config.model_dump()})
    return {"ok": True}

@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str, db: AsyncClient = Depends(get_db)):
    repo = DatasetRepository(db)

    # Fetch record first to get storage_path for cleanup
    doc = await repo.get(dataset_id)
    if not doc:
        raise HTTPException(404, "Dataset not found")

    storage_path = doc.get("storage_path", "")

    # Delete ann_records rows first (FK constraint)
    await db.table("ann_records").delete().eq("dataset_id", dataset_id).execute()

    # Delete the dataset DB record
    await repo.delete(dataset_id)

    # Clean up Supabase Storage file (best-effort — don't fail if missing)
    if storage_path:
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: delete_raw(storage_path)
            )
        except Exception:
            pass  # Don't surface storage cleanup errors to the caller

    return {"ok": True}
