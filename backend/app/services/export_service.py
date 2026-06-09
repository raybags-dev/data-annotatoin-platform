"""Export annotated dataset to CSV / JSON / Excel."""
from __future__ import annotations
import io, json
from datetime import datetime
import pandas as pd
from supabase import AsyncClient

class ExportService:
    def __init__(self, db: AsyncClient):
        self.db = db

    async def _get_records(self, dataset_id: str) -> list[dict]:
        res = await self.db.table("ann_records").select("*").eq("dataset_id", dataset_id).order("row_index").execute()
        rows = []
        for r in res.data:
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
        return pd.DataFrame(rows).to_csv(index=False).encode()

    async def to_json(self, dataset_id: str) -> bytes:
        rows = await self._get_records(dataset_id)
        return json.dumps(rows, default=str, indent=2).encode()

    async def to_excel(self, dataset_id: str) -> bytes:
        rows = await self._get_records(dataset_id)
        buf = io.BytesIO()
        pd.DataFrame(rows).to_excel(buf, index=False)
        return buf.getvalue()

    async def processing_report(self, dataset_id: str) -> dict:
        res = await self.db.table("ann_datasets").select("*").eq("id", dataset_id).execute()
        if not res.data:
            raise ValueError("Dataset not found")
        doc = res.data[0]

        ann_res = await self.db.table("ann_records").select("annotation").eq("dataset_id", dataset_id).execute()
        label_dist: dict[str, int] = {}
        for r in ann_res.data:
            ann = r.get("annotation")
            if ann and ann.get("label"):
                lbl = ann["label"]
                label_dist[lbl] = label_dist.get(lbl, 0) + 1

        history = doc.pop("processing_history", [])
        return {
            "dataset": doc,
            "label_distribution": label_dist,
            "processing_history": history,
            "generated_at": datetime.utcnow().isoformat(),
        }
