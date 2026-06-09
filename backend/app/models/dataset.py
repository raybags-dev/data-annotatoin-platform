from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field

class SchemaField(BaseModel):
    dtype: str
    nullable: bool = False
    unique_count: int = 0
    sample_values: list[Any] = []

class ValidationReport(BaseModel):
    total_rows: int = 0
    duplicate_rows: int = 0
    missing_value_counts: dict[str, int] = {}
    type_issues: dict[str, str] = {}
    schema_fields: dict[str, SchemaField] = {}
    issues: list[str] = []

class CleaningReport(BaseModel):
    rows_before: int = 0
    rows_after: int = 0
    duplicates_removed: int = 0
    missing_filled: int = 0
    missing_dropped: int = 0
    text_normalized: int = 0

class ProcessingHistoryEntry(BaseModel):
    stage: str
    status: str  # running | completed | failed
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    metrics: dict[str, Any] = {}
    error: str | None = None

class LabelingConfig(BaseModel):
    categories: list[str] = []
    label_column_hint: str | None = None
    model: str = "llama3.2:3b"
