"""Stage 3 — dedup, normalize, fill/drop missing values."""
from __future__ import annotations
import re
from datetime import datetime
from bson import ObjectId
from app.pipeline.base import PipelineStage

class CleanStage(PipelineStage):
    name = "clean"

    async def run(self, dataset_id: str, **kwargs) -> dict:
        await self._mark_running(dataset_id)
        try:
            records = await self.db.records.find({"dataset_id": dataset_id}).to_list(None)
            if not records:
                raise ValueError("No records — run ingest first")

            rows_before = len(records)
            seen, unique_records, dups = set(), [], 0
            for r in records:
                key = str(sorted(r["raw_data"].items()))
                if key in seen:
                    dups += 1
                    continue
                seen.add(key)
                unique_records.append(r)

            missing_filled = missing_dropped = text_norm = 0
            for r in unique_records:
                cleaned = {}
                for k, v in r["raw_data"].items():
                    if v is None or v == "":
                        cleaned[k] = None
                        missing_dropped += 1
                    elif isinstance(v, str):
                        norm = re.sub(r"s+", " ", v.strip().lower())
                        cleaned[k] = norm
                        if norm != v:
                            text_norm += 1
                    else:
                        cleaned[k] = v
                await self.db.records.update_one(
                    {"_id": r["_id"]},
                    {"$set": {"cleaned_data": cleaned, "updated_at": datetime.utcnow()}}
                )

            # Remove duplicate records
            all_ids = [r["_id"] for r in records]
            keep_ids = [r["_id"] for r in unique_records]
            remove_ids = [i for i in all_ids if i not in set(keep_ids)]
            if remove_ids:
                await self.db.records.delete_many({"_id": {"$in": remove_ids}})

            report = {
                "rows_before": rows_before,
                "rows_after": len(unique_records),
                "duplicates_removed": dups,
                "missing_filled": missing_filled,
                "missing_dropped": missing_dropped,
                "text_normalized": text_norm,
            }
            await self.db.datasets.update_one(
                {"_id": ObjectId(dataset_id)},
                {"$set": {"cleaning_report": report, "row_count": len(unique_records)}}
            )
            await self._mark_done(dataset_id, report, "cleaned")
            return report
        except Exception as e:
            await self._mark_failed(dataset_id, str(e))
            raise
