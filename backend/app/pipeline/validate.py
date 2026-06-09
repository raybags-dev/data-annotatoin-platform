"""Stage 2 — schema detection, type inference, issue reporting."""
from __future__ import annotations
from datetime import datetime
from bson import ObjectId
from app.pipeline.base import PipelineStage

class ValidateStage(PipelineStage):
    name = "validate"

    async def run(self, dataset_id: str, **kwargs) -> dict:
        await self._mark_running(dataset_id)
        try:
            records = await self.db.records.find({"dataset_id": dataset_id}).to_list(None)
            if not records:
                raise ValueError("No records found — run ingest first")

            rows = [r["raw_data"] for r in records]
            columns = list(rows[0].keys()) if rows else []
            total = len(rows)

            schema_fields = {}
            missing_counts: dict[str, int] = {}
            type_issues: dict[str, str] = {}

            for col in columns:
                vals = [r.get(col) for r in rows]
                non_null = [v for v in vals if v is not None and v != ""]
                null_count = total - len(non_null)
                missing_counts[col] = null_count

                # Type inference
                numeric, dates = 0, 0
                for v in non_null[:100]:
                    try: float(v); numeric += 1
                    except: pass
                    try:
                        from dateutil.parser import parse
                        parse(str(v)); dates += 1
                    except: pass

                if numeric == len(non_null[:100]):
                    dtype = "numeric"
                elif dates > len(non_null[:100]) * 0.8:
                    dtype = "datetime"
                else:
                    dtype = "text"

                schema_fields[col] = {
                    "dtype": dtype,
                    "nullable": null_count > 0,
                    "unique_count": len(set(str(v) for v in non_null)),
                    "sample_values": [str(v) for v in non_null[:3]],
                }

            # Duplicate detection
            row_strs = [str(sorted(r.items())) for r in rows]
            dup_count = total - len(set(row_strs))

            issues = []
            if dup_count:
                issues.append(f"{dup_count} duplicate rows detected")
            for col, cnt in missing_counts.items():
                if cnt / total > 0.2:
                    issues.append(f"Column '{col}' has {cnt}/{total} missing values ({cnt*100//total}%)")

            report = {
                "total_rows": total,
                "duplicate_rows": dup_count,
                "missing_value_counts": missing_counts,
                "type_issues": type_issues,
                "schema_fields": schema_fields,
                "issues": issues,
            }
            await self.db.datasets.update_one(
                {"_id": ObjectId(dataset_id)},
                {"$set": {"validation_report": report}}
            )
            await self._mark_done(dataset_id, {"issues_found": len(issues)}, "validated")
            return report
        except Exception as e:
            await self._mark_failed(dataset_id, str(e))
            raise
