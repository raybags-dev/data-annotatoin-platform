from __future__ import annotations
from datetime import datetime
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

class DatasetRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db.datasets

    async def create(self, doc: dict) -> str:
        doc["created_at"] = doc["updated_at"] = datetime.utcnow()
        result = await self.col.insert_one(doc)
        return str(result.inserted_id)

    async def get(self, dataset_id: str) -> dict | None:
        doc = await self.col.find_one({"_id": ObjectId(dataset_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def list_all(self, skip: int = 0, limit: int = 50) -> list[dict]:
        docs = await self.col.find({}).sort("created_at", -1).skip(skip).limit(limit).to_list(None)
        for d in docs:
            d["_id"] = str(d["_id"])
        return docs

    async def update(self, dataset_id: str, patch: dict) -> None:
        patch["updated_at"] = datetime.utcnow()
        await self.col.update_one({"_id": ObjectId(dataset_id)}, {"$set": patch})

    async def delete(self, dataset_id: str) -> None:
        await self.col.delete_one({"_id": ObjectId(dataset_id)})

    async def count(self) -> int:
        return await self.col.count_documents({})
