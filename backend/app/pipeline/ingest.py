"""Stage 1 — load raw file from Supabase into MongoDB records collection."""
from __future__ import annotations
import io, json
from datetime import datetime
import pandas as pd
from bson import ObjectId
from app.pipeline.base import PipelineStage
from app.core.storage import download_raw

class IngestStage(PipelineStage):
    name = "ingest"

    async def run(self, dataset_id: str, **kwargs) -> dict:
        await self._mark_running(dataset_id)
        try:
            doc = await self.db.datasets.find_one({"_id": ObjectId(dataset_id)})
            if not doc:
                raise ValueError("Dataset not found")

            raw_bytes = download_raw(doc["storage_path"])
            df = self._parse(raw_bytes, doc["file_type"])

            records = []
            for i, row in df.iterrows():
                records.append({
                    "dataset_id": dataset_id,
                    "row_index": int(i),
                    "raw_data": {k: str(v) if pd.notna(v) else None for k, v in row.items()},
                    "cleaned_data": {},
                    "annotation": None,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                })

            # Clear old records then insert fresh
            await self.db.records.delete_many({"dataset_id": dataset_id})
            if records:
                await self.db.records.insert_many(records)

            metrics = {"rows_ingested": len(records), "columns": list(df.columns)}
            await self.db.datasets.update_one(
                {"_id": ObjectId(dataset_id)},
                {"$set": {"row_count": len(records), "column_count": len(df.columns), "columns": list(df.columns)}}
            )
            await self._mark_done(dataset_id, metrics, "ingested")
            return metrics
        except Exception as e:
            await self._mark_failed(dataset_id, str(e))
            raise

    def _parse(self, data: bytes, file_type: str) -> pd.DataFrame:
        if file_type == "csv":
            return pd.read_csv(io.BytesIO(data))
        elif file_type == "json":
            return pd.read_json(io.BytesIO(data))
        elif file_type in ("excel", "xlsx"):
            return pd.read_excel(io.BytesIO(data))
        elif file_type == "txt":
            lines = data.decode("utf-8").splitlines()
            return pd.DataFrame({"text": lines})
        raise ValueError(f"Unsupported file type: {file_type}")
