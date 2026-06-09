from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel

class AnnotationData(BaseModel):
    label: str
    confidence: float = 0.0
    model: str = ""
    reasoning: str = ""
    human_reviewed: bool = False
    human_label: str | None = None
    status: str = "pending"  # pending | approved | rejected
    reviewed_at: datetime | None = None

class AnnotationReview(BaseModel):
    record_id: str
    action: str  # approve | reject | override
    human_label: str | None = None
