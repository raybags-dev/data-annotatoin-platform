from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from supabase import AsyncClient

TABLE = "ann_datasets"

class PipelineStage(ABC):
    name: str = "base"

    def __init__(self, db: AsyncClient):
        self.db = db

    @abstractmethod
    async def run(self, dataset_id: str, **kwargs) -> dict: ...

    async def _get_history(self, dataset_id: str) -> list:
        res = await self.db.table(TABLE).select("processing_history").eq("id", dataset_id).execute()
        return (res.data[0].get("processing_history") or []) if res.data else []

    async def _mark_running(self, dataset_id: str) -> None:
        history = await self._get_history(dataset_id)
        history.append({
            "stage": self.name,
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "metrics": {},
            "error": None,
        })
        await self.db.table(TABLE).update({
            "status": self.name + "ing",
            "processing_history": history,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", dataset_id).execute()

    async def _mark_done(self, dataset_id: str, metrics: dict, new_status: str) -> None:
        now = datetime.utcnow().isoformat()
        history = await self._get_history(dataset_id)
        for i in range(len(history) - 1, -1, -1):
            if history[i].get("stage") == self.name and history[i].get("status") == "running":
                history[i]["status"] = "completed"
                history[i]["completed_at"] = now
                history[i]["metrics"] = metrics
                break
        await self.db.table(TABLE).update({
            "status": new_status,
            "processing_history": history,
            "updated_at": now,
        }).eq("id", dataset_id).execute()

    async def _mark_failed(self, dataset_id: str, error: str) -> None:
        now = datetime.utcnow().isoformat()
        history = await self._get_history(dataset_id)
        for i in range(len(history) - 1, -1, -1):
            if history[i].get("stage") == self.name and history[i].get("status") == "running":
                history[i]["status"] = "failed"
                history[i]["completed_at"] = now
                history[i]["error"] = error
                break
        await self.db.table(TABLE).update({
            "status": self.name + "_failed",
            "processing_history": history,
            "updated_at": now,
        }).eq("id", dataset_id).execute()
