from __future__ import annotations
from datetime import datetime
from supabase import AsyncClient

TABLE = "ann_datasets"

class DatasetRepository:
    def __init__(self, db: AsyncClient):
        self.db = db

    async def create(self, doc: dict) -> str:
        now = datetime.utcnow().isoformat()
        doc = {**doc, "created_at": now, "updated_at": now}
        res = await self.db.table(TABLE).insert(doc).execute()
        return str(res.data[0]["id"])

    async def get(self, dataset_id: str) -> dict | None:
        res = await self.db.table(TABLE).select("*").eq("id", dataset_id).execute()
        return res.data[0] if res.data else None

    async def list_all(self, skip: int = 0, limit: int = 50) -> list[dict]:
        res = (
            await self.db.table(TABLE)
            .select("*")
            .order("created_at", desc=True)
            .range(skip, skip + limit - 1)
            .execute()
        )
        return res.data

    async def update(self, dataset_id: str, patch: dict) -> None:
        patch = {**patch, "updated_at": datetime.utcnow().isoformat()}
        await self.db.table(TABLE).update(patch).eq("id", dataset_id).execute()

    async def delete(self, dataset_id: str) -> None:
        await self.db.table(TABLE).delete().eq("id", dataset_id).execute()

    async def count(self) -> int:
        res = await self.db.table(TABLE).select("id", count="exact").execute()
        return res.count or 0
