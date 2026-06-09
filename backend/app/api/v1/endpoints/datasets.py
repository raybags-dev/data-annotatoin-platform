from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from supabase import AsyncClient
from app.core.database import get_db
from app.core.storage import upload_raw
from app.repositories.dataset_repo import DatasetRepository
from app.models.dataset import LabelingConfig

router = APIRouter()

def _repo(db: AsyncClient = Depends(get_db)) -> DatasetRepository:
    return DatasetRepository(db)

@router.get("")
async def list_datasets(repo: DatasetRepository = Depends(_repo)):
    return await repo.list_all()

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
    await db.table("ann_records").delete().eq("dataset_id", dataset_id).execute()
    await repo.delete(dataset_id)
    return {"ok": True}
