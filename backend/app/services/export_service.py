"""Export annotated dataset to CSV / JSON / Excel."""
from __future__ import annotations
import io, json
from datetime import datetime
import pandas as pd
from motor.motor_asyncio import AsyncIOMotorDatabase

class ExportService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def _get_records(self, dataset_id: str) -> list[dict]:
        records = await self.db.records.find({"dataset_id": dataset_id}).to_list(None)
        rows = []
        for r in records:
            row = dict(r.get("cleaned_data") or r.get("raw_data") or {})
            ann = r.get("annotation")
            if ann:
                row["__label"] = ann.get("human_label") or ann.get("label")
                row["__confidence"] = ann.get("confidence")
                row["__status"] = ann.get("status")
            rows.append(row)
        return rows

    async def to_csv(self, dataset_id: str) -> bytes:
        rows = await self._get_records(dataset_id)
        df = pd.DataFrame(rows)
        return df.to_csv(index=False).encode()

    async def to_json(self, dataset_id: str) -> bytes:
        rows = await self._get_records(dataset_id)
        return json.dumps(rows, default=str, indent=2).encode()

    async def to_excel(self, dataset_id: str) -> bytes:
        rows = await self._get_records(dataset_id)
        df = pd.DataFrame(rows)
        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        return buf.getvalue()

    async def processing_report(self, dataset_id: str) -> dict:
        from bson import ObjectId
        doc = await self.db.datasets.find_one({"_id": ObjectId(dataset_id)})
        if not doc:
            raise ValueError("Dataset not found")
        doc["_id"] = str(doc["_id"])
        pipeline = [
            {"$match": {"dataset_id": dataset_id}},
            {"$group": {"_id": "$annotation.label", "count": {"$sum": 1}}},
        ]
        label_dist = {r["_id"]: r["count"] for r in await self.db.records.aggregate(pipeline).to_list(None) if r["_id"]}
        return {
            "dataset": {k: v for k, v in doc.items() if k not in ("processing_history",)},
            "label_distribution": label_dist,
            "processing_history": doc.get("processing_history", []),
            "generated_at": datetime.utcnow().isoformat(),
        }
