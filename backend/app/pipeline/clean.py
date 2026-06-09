"""Stage 3 — dedup, normalize, fill/drop missing values."""
from __future__ import annotations
import re
from datetime import datetime
from app.pipeline.base import PipelineStage

class CleanStage(PipelineStage):
    name = "clean"

    async def run(self, dataset_id: str, **kwargs) -> dict:
        await self._mark_running(dataset_id)
        try:
            res = await self.db.table("ann_records").select("*").eq("dataset_id", dataset_id).order("row_index").execute()
            if not res.data:
                raise ValueError("No records — run ingest first")

            records = res.data
            rows_before = len(records)

            seen, unique_records, dups = set(), [], 0
            for r in records:
                key = str(sorted(r["raw_data"].items()))
                if key in seen:
                    dups += 1
                    continue
                seen.add(key)
                unique_records.append(r)

            keep_ids = {r["id"] for r in unique_records}
            remove_ids = [r["id"] for r in records if r["id"] not in keep_ids]

            missing_dropped = text_norm = 0
            now = datetime.utcnow().isoformat()

            for r in unique_records:
                cleaned = {}
                for k, v in r["raw_data"].items():
                    if v is None or v == "":
                        cleaned[k] = None
                        missing_dropped += 1
                    elif isinstance(v, str):
                        norm = re.sub(r"\s+", " ", v.strip().lower())
                        cleaned[k] = norm
                        if norm != v:
                            text_norm += 1
                    else:
                        cleaned[k] = v
                await self.db.table("ann_records").update({
                    "cleaned_data": cleaned,
                    "updated_at": now,
                }).eq("id", r["id"]).execute()

            for rid in remove_ids:
                await self.db.table("ann_records").delete().eq("id", rid).execute()

            report = {
                "rows_before": rows_before,
                "rows_after": len(unique_records),
                "duplicates_removed": dups,
                "missing_filled": 0,
                "missing_dropped": missing_dropped,
                "text_normalized": text_norm,
            }
            await self.db.table("ann_datasets").update({
                "cleaning_report": report,
                "row_count": len(unique_records),
            }).eq("id", dataset_id).execute()
            await self._mark_done(dataset_id, report, "cleaned")
            return report
        except Exception as e:
            await self._mark_failed(dataset_id, str(e))
            raise
