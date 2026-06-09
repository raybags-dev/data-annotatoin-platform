from __future__ import annotations
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

class AnnotationRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db.records

    async def list_for_dataset(self, dataset_id: str, skip: int = 0, limit: int = 100) -> list[dict]:
        docs = await self.col.find({"dataset_id": dataset_id}).skip(skip).limit(limit).to_list(None)
        for d in docs:
            d["_id"] = str(d["_id"])
        return docs

    async def get(self, record_id: str) -> dict | None:
        doc = await self.col.find_one({"_id": ObjectId(record_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def update_annotation(self, record_id: str, patch: dict) -> None:
        await self.col.update_one(
            {"_id": ObjectId(record_id)},
            {"$set": {"annotation": patch, "updated_at": datetime.utcnow()}}
        )

    async def count_by_status(self, dataset_id: str) -> dict[str, int]:
        pipeline = [
            {"$match": {"dataset_id": dataset_id}},
            {"$group": {"_id": "$annotation.status", "count": {"$sum": 1}}},
        ]
        result = await self.col.aggregate(pipeline).to_list(None)
        return {r["_id"] or "unannotated": r["count"] for r in result}

    async def label_distribution(self, dataset_id: str) -> dict[str, int]:
        pipeline = [
            {"$match": {"dataset_id": dataset_id, "annotation": {"$ne": None}}},
            {"$group": {"_id": "$annotation.label", "count": {"$sum": 1}}},
        ]
        result = await self.col.aggregate(pipeline).to_list(None)
        return {r["_id"]: r["count"] for r in result if r["_id"]}
