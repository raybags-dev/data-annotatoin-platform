from __future__ import annotations
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field
from bson import ObjectId

class PyObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    @classmethod
    def validate(cls, v, _info=None):
        if not ObjectId.is_valid(str(v)):
            raise ValueError("Invalid ObjectId")
        return str(v)

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
    label_column_hint: str | None = None  # column to focus on for classification
    model: str = "llama3.2:3b"

class DatasetDocument(BaseModel):
    id: PyObjectId | None = Field(default=None, alias="_id")
    name: str
    filename: str
    file_type: str  # csv | json | excel | txt
    storage_path: str
    storage_url: str = ""
    status: str = "uploaded"  # uploaded|validating|validated|cleaning|cleaned|labeling|labeled|reviewing|exported
    row_count: int = 0
    column_count: int = 0
    columns: list[str] = []
    validation_report: ValidationReport | None = None
    cleaning_report: CleaningReport | None = None
    labeling_config: LabelingConfig = Field(default_factory=LabelingConfig)
    processing_history: list[ProcessingHistoryEntry] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

class DatasetCreate(BaseModel):
    name: str
    filename: str
    file_type: str
    storage_path: str

class DatasetUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    labeling_config: LabelingConfig | None = None
