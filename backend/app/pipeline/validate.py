"""Stage 2 — schema detection, type inference, issue reporting."""
from __future__ import annotations
from app.pipeline.base import PipelineStage

class ValidateStage(PipelineStage):
    name = "validate"

    async def run(self, dataset_id: str, **kwargs) -> dict:
        await self._mark_running(dataset_id)
        try:
            res = await self.db.table("ann_records").select("raw_data").eq("dataset_id", dataset_id).execute()
            if not res.data:
                raise ValueError("No records found — run ingest first")

            rows = [r["raw_data"] for r in res.data]
            columns = list(rows[0].keys()) if rows else []
            total = len(rows)

            schema_fields: dict = {}
            missing_counts: dict[str, int] = {}

            for col in columns:
                vals = [r.get(col) for r in rows]
                non_null = [v for v in vals if v is not None and v != ""]
                null_count = total - len(non_null)
                missing_counts[col] = null_count

                numeric, dates = 0, 0
                for v in non_null[:100]:
                    try:
                        float(v)
                        numeric += 1
                    except Exception:
                        pass
                    try:
                        from dateutil.parser import parse
                        parse(str(v))
                        dates += 1
                    except Exception:
                        pass

                sample = len(non_null[:100])
                if sample and numeric == sample:
                    dtype = "numeric"
                elif sample and dates > sample * 0.8:
                    dtype = "datetime"
                else:
                    dtype = "text"

                schema_fields[col] = {
                    "dtype": dtype,
                    "nullable": null_count > 0,
                    "unique_count": len(set(str(v) for v in non_null)),
                    "sample_values": [str(v) for v in non_null[:3]],
                }

            row_strs = [str(sorted(r.items())) for r in rows]
            dup_count = total - len(set(row_strs))

            issues = []
            if dup_count:
                issues.append(f"{dup_count} duplicate rows detected")
            for col, cnt in missing_counts.items():
                if total and cnt / total > 0.2:
                    issues.append(f"Column '{col}' has {cnt}/{total} missing values ({cnt * 100 // total}%)")

            report = {
                "total_rows": total,
                "duplicate_rows": dup_count,
                "missing_value_counts": missing_counts,
                "type_issues": {},
                "schema_fields": schema_fields,
                "issues": issues,
            }
            await self.db.table("ann_datasets").update({"validation_report": report}).eq("id", dataset_id).execute()
            await self._mark_done(dataset_id, {"issues_found": len(issues)}, "validated")
            return report
        except Exception as e:
            await self._mark_failed(dataset_id, str(e))
            raise
