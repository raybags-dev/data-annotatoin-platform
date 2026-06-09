from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from app.models.dataset import PyObjectId

class AnnotationData(BaseModel):
    label: str
    confidence: float = 0.0
    model: str = ""
    reasoning: str = ""
    human_reviewed: bool = False
    human_label: str | None = None
    status: str = "pending"  # pending | approved | rejected
    reviewed_at: datetime | None = None

class RecordDocument(BaseModel):
    id: PyObjectId | None = Field(default=None, alias="_id")
    dataset_id: str
    row_index: int
    raw_data: dict[str, Any] = {}
    cleaned_data: dict[str, Any] = {}
    annotation: AnnotationData | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

class AnnotationReview(BaseModel):
    record_id: str
    action: str  # approve | reject | override
    human_label: str | None = None
