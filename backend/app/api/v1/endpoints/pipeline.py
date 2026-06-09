from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.database import get_db
from app.pipeline.orchestrator import run_stage, run_pipeline, FULL_PIPELINE

router = APIRouter()

class RunRequest(BaseModel):
    stages: list[str] | None = None  # None = full pipeline

@router.post("/{dataset_id}/run")
async def run_full(dataset_id: str, req: RunRequest = RunRequest(), db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        results = await run_pipeline(db, dataset_id, req.stages)
        return {"dataset_id": dataset_id, "results": results}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post("/{dataset_id}/stage/{stage}")
async def run_one_stage(dataset_id: str, stage: str, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        result = await run_stage(db, dataset_id, stage)
        return {"dataset_id": dataset_id, "stage": stage, "result": result}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.get("/stages")
async def list_stages():
    return {"stages": FULL_PIPELINE, "descriptions": {
        "ingest": "Load raw file from Supabase into MongoDB records",
        "validate": "Schema detection, type inference, issue reporting",
        "clean": "Dedup, normalize text, handle missing values",
        "label": "AI annotation via Ollama with confidence scores",
    }}
