"""Stage 4 — AI annotation via Ollama. Re-runnable."""
from __future__ import annotations
import json, httpx
from datetime import datetime
from bson import ObjectId
from app.pipeline.base import PipelineStage
from app.core.config import settings

PROMPT = """You are a data annotation assistant. Classify the following record into exactly one of these categories: {categories}

Record (JSON): {record}

Respond with ONLY valid JSON in this format:
{{"label": "<one of the categories>", "confidence": <0.0-1.0>, "reasoning": "<one sentence>"}}"""

class LabelStage(PipelineStage):
    name = "label"

    async def run(self, dataset_id: str, **kwargs) -> dict:
        await self._mark_running(dataset_id)
        try:
            doc = await self.db.datasets.find_one({"_id": ObjectId(dataset_id)})
            if not doc:
                raise ValueError("Dataset not found")

            config = doc.get("labeling_config", {})
            categories = config.get("categories", [])
            if not categories:
                raise ValueError("No labeling categories configured. Set labeling_config.categories first.")

            model = config.get("model", settings.OLLAMA_MODEL)
            records = await self.db.records.find({"dataset_id": dataset_id}).to_list(None)

            labeled = failed = 0
            async with httpx.AsyncClient(timeout=120) as client:
                for r in records:
                    data = r.get("cleaned_data") or r.get("raw_data") or {}
                    prompt = PROMPT.format(
                        categories=", ".join(categories),
                        record=json.dumps(data, default=str)[:1000],
                    )
                    try:
                        resp = await client.post(
                            f"{settings.OLLAMA_URL}/api/generate",
                            json={"model": model, "prompt": prompt, "stream": False},
                        )
                        resp.raise_for_status()
                        raw = resp.json().get("response", "")
                        # Extract JSON from response
                        start = raw.find("{")
                        end = raw.rfind("}") + 1
                        parsed = json.loads(raw[start:end]) if start >= 0 else {}
                        annotation = {
                            "label": parsed.get("label", categories[0]),
                            "confidence": float(parsed.get("confidence", 0.5)),
                            "model": model,
                            "reasoning": parsed.get("reasoning", ""),
                            "human_reviewed": False,
                            "human_label": None,
                            "status": "pending",
                            "reviewed_at": None,
                        }
                        labeled += 1
                    except Exception as ex:
                        annotation = {
                            "label": categories[0],
                            "confidence": 0.0,
                            "model": model,
                            "reasoning": f"Error: {ex}",
                            "human_reviewed": False,
                            "human_label": None,
                            "status": "pending",
                            "reviewed_at": None,
                        }
                        failed += 1

                    await self.db.records.update_one(
                        {"_id": r["_id"]},
                        {"$set": {"annotation": annotation, "updated_at": datetime.utcnow()}}
                    )

            metrics = {"total": len(records), "labeled": labeled, "failed": failed}
            await self._mark_done(dataset_id, metrics, "labeled")
            return metrics
        except Exception as e:
            await self._mark_failed(dataset_id, str(e))
            raise
