from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import AsyncClient
from app.core.database import get_db
from app.repositories.annotation_repo import AnnotationRepository

router = APIRouter()

def _repo(db: AsyncClient = Depends(get_db)) -> AnnotationRepository:
    return AnnotationRepository(db)

@router.get("/{dataset_id}/records")
async def list_records(dataset_id: str, skip: int = 0, limit: int = 50, repo: AnnotationRepository = Depends(_repo)):
    return await repo.list_for_dataset(dataset_id, skip, limit)

@router.get("/{dataset_id}/stats")
async def annotation_stats(dataset_id: str, repo: AnnotationRepository = Depends(_repo)):
    return {
        "by_status": await repo.count_by_status(dataset_id),
        "label_distribution": await repo.label_distribution(dataset_id),
    }

class ReviewAction(BaseModel):
    action: str  # approve | reject | override
    human_label: str | None = None

@router.patch("/record/{record_id}/review")
async def review_record(record_id: str, body: ReviewAction, repo: AnnotationRepository = Depends(_repo)):
    rec = await repo.get(record_id)
    if not rec:
        raise HTTPException(404, "Record not found")
    ann = rec.get("annotation") or {}
    now = datetime.utcnow().isoformat()
    if body.action == "approve":
        ann.update({"status": "approved", "human_reviewed": True, "reviewed_at": now})
    elif body.action == "reject":
        ann.update({"status": "rejected", "human_reviewed": True, "reviewed_at": now})
    elif body.action == "override":
        if not body.human_label:
            raise HTTPException(400, "human_label required for override")
        ann.update({"status": "approved", "human_reviewed": True, "human_label": body.human_label, "reviewed_at": now})
    await repo.update_annotation(record_id, ann)
    return {"ok": True}

@router.post("/{dataset_id}/approve-all")
async def approve_all_pending(dataset_id: str, db: AsyncClient = Depends(get_db)):
    res = await db.table("ann_records").select("id,annotation").eq("dataset_id", dataset_id).execute()
    now = datetime.utcnow().isoformat()
    approved = 0
    for r in res.data:
        ann = r.get("annotation") or {}
        if ann.get("status") == "pending":
            ann.update({"status": "approved", "human_reviewed": True, "reviewed_at": now})
            await db.table("ann_records").update({
                "annotation": ann, "updated_at": now,
            }).eq("id", r["id"]).execute()
            approved += 1
    return {"approved": approved}
