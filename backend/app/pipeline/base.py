from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase

class PipelineStage(ABC):
    name: str = "base"

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    @abstractmethod
    async def run(self, dataset_id: str, **kwargs) -> dict:
        """Execute the stage. Returns metrics dict."""
        ...

    async def _mark_running(self, dataset_id: str) -> None:
        from bson import ObjectId
        await self.db.datasets.update_one(
            {"_id": ObjectId(dataset_id)},
            {
                "$set": {"status": self.name + "ing", "updated_at": datetime.utcnow()},
                "$push": {"processing_history": {
                    "stage": self.name, "status": "running",
                    "started_at": datetime.utcnow(), "completed_at": None, "metrics": {}, "error": None
                }}
            }
        )

    async def _mark_done(self, dataset_id: str, metrics: dict, new_status: str) -> None:
        from bson import ObjectId
        now = datetime.utcnow()
        await self.db.datasets.update_one(
            {"_id": ObjectId(dataset_id), "processing_history.stage": self.name, "processing_history.status": "running"},
            {
                "$set": {
                    "status": new_status, "updated_at": now,
                    "processing_history.$.status": "completed",
                    "processing_history.$.completed_at": now,
                    "processing_history.$.metrics": metrics,
                }
            }
        )

    async def _mark_failed(self, dataset_id: str, error: str) -> None:
        from bson import ObjectId
        now = datetime.utcnow()
        await self.db.datasets.update_one(
            {"_id": ObjectId(dataset_id), "processing_history.stage": self.name, "processing_history.status": "running"},
            {
                "$set": {
                    "status": self.name + "_failed", "updated_at": now,
                    "processing_history.$.status": "failed",
                    "processing_history.$.completed_at": now,
                    "processing_history.$.error": error,
                }
            }
        )
