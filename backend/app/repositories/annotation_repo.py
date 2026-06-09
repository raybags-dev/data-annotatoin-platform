from __future__ import annotations
from datetime import datetime
from supabase._async.client import AsyncClient

TABLE = "ann_records"

class AnnotationRepository:
    def __init__(self, db: AsyncClient):
        self.db = db

    async def list_for_dataset(self, dataset_id: str, skip: int = 0, limit: int = 100) -> list[dict]:
        res = (
            await self.db.table(TABLE)
            .select("*")
            .eq("dataset_id", dataset_id)
            .order("row_index")
            .range(skip, skip + limit - 1)
            .execute()
        )
        return res.data

    async def get(self, record_id: str) -> dict | None:
        res = await self.db.table(TABLE).select("*").eq("id", record_id).execute()
        return res.data[0] if res.data else None

    async def update_annotation(self, record_id: str, annotation: dict) -> None:
        await self.db.table(TABLE).update({
            "annotation": annotation,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", record_id).execute()

    async def count_by_status(self, dataset_id: str) -> dict[str, int]:
        res = await self.db.table(TABLE).select("annotation").eq("dataset_id", dataset_id).execute()
        counts: dict[str, int] = {}
        for r in res.data:
            ann = r.get("annotation")
            status = ann.get("status") if ann else "unannotated"
            counts[status or "unannotated"] = counts.get(status or "unannotated", 0) + 1
        return counts

    async def label_distribution(self, dataset_id: str) -> dict[str, int]:
        res = await self.db.table(TABLE).select("annotation").eq("dataset_id", dataset_id).execute()
        dist: dict[str, int] = {}
        for r in res.data:
            ann = r.get("annotation")
            if ann and ann.get("label"):
                label = ann["label"]
                dist[label] = dist.get(label, 0) + 1
        return dist
