"""Run the full pipeline or individual named stages."""
from __future__ import annotations
from supabase import AsyncClient
from app.pipeline.ingest import IngestStage
from app.pipeline.validate import ValidateStage
from app.pipeline.clean import CleanStage
from app.pipeline.label import LabelStage

STAGES = {
    "ingest": IngestStage,
    "validate": ValidateStage,
    "clean": CleanStage,
    "label": LabelStage,
}

FULL_PIPELINE = ["ingest", "validate", "clean", "label"]

async def run_stage(db: AsyncClient, dataset_id: str, stage: str, **kwargs) -> dict:
    cls = STAGES.get(stage)
    if not cls:
        raise ValueError(f"Unknown stage: {stage}. Choose from {list(STAGES)}")
    return await cls(db).run(dataset_id, **kwargs)

async def run_pipeline(db: AsyncClient, dataset_id: str, stages: list[str] | None = None, **kwargs) -> dict:
    to_run = stages or FULL_PIPELINE
    results = {}
    for stage in to_run:
        results[stage] = await run_stage(db, dataset_id, stage, **kwargs)
    return results
