"""Stage 1 — load raw file from Supabase Storage into ann_records table."""
from __future__ import annotations
import io
from datetime import datetime
import pandas as pd
from app.pipeline.base import PipelineStage
from app.core.storage import download_raw

class IngestStage(PipelineStage):
    name = "ingest"

    async def run(self, dataset_id: str, **kwargs) -> dict:
        await self._mark_running(dataset_id)
        try:
            res = await self.db.table("ann_datasets").select("*").eq("id", dataset_id).execute()
            if not res.data:
                raise ValueError("Dataset not found")
            doc = res.data[0]

            raw_bytes = download_raw(doc["storage_path"])
            df = self._parse(raw_bytes, doc["file_type"])

            records = [
                {
                    "dataset_id": dataset_id,
                    "row_index": int(i),
                    "raw_data": {k: str(v) if pd.notna(v) else None for k, v in row.items()},
                    "cleaned_data": {},
                    "annotation": None,
                }
                for i, row in df.iterrows()
            ]

            # Clear old records then insert fresh
            await self.db.table("ann_records").delete().eq("dataset_id", dataset_id).execute()
            if records:
                # Insert in batches of 500 to avoid request size limits
                for i in range(0, len(records), 500):
                    await self.db.table("ann_records").insert(records[i:i + 500]).execute()

            metrics = {"rows_ingested": len(records), "columns": list(df.columns)}
            await self.db.table("ann_datasets").update({
                "row_count": len(records),
                "column_count": len(df.columns),
                "columns": list(df.columns),
                "updated_at": datetime.utcnow().isoformat(),
            }).eq("id", dataset_id).execute()
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
