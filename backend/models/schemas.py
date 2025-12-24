"""Pydantic models for API request/response schemas."""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


# === Dataset Models ===

class DatasetInfo(BaseModel):
    """Basic dataset metadata."""
    id: str
    name: str
    rows: int
    columns: int
    size_bytes: int
    uploaded_at: datetime


class ColumnInfo(BaseModel):
    """Column profile information."""
    name: str
    dtype: Literal["numeric", "categorical", "datetime", "boolean", "text"]
    null_count: int
    null_percentage: float
    unique_count: int
    sample_values: list[str] = Field(default_factory=list)


class DatasetProfile(BaseModel):
    """Complete dataset profile."""
    dataset: DatasetInfo
    columns: list[ColumnInfo]


# === Health Check Models ===

class HealthIssue(BaseModel):
    """A single data quality issue."""
    column: str
    issue_type: Literal["missing", "duplicate", "format", "outlier"]
    severity: Literal["low", "medium", "high"]
    count: int
    percentage: float
    description: str


class HealthCheckResult(BaseModel):
    """Result of data health check."""
    dataset_id: str
    total_rows: int
    total_columns: int
    issues: list[HealthIssue]
    overall_health: Literal["good", "fair", "poor"]


# === Insight Models ===

class Insight(BaseModel):
    """A single data insight."""
    id: str
    insight_type: Literal["trend", "ranking", "concentration", "anomaly", "summary"]
    title: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    data: Optional[dict] = None


class InsightResult(BaseModel):
    """Result of insight generation."""
    dataset_id: str
    insights: list[Insight]
    generated_at: datetime


# === Suggested Question Models ===

class SuggestedQuestion(BaseModel):
    """A dataset-aware EDA question tied to a specific column."""

    id: str
    text: str
    column: str
    type: Literal["time", "category", "numeric", "quality"]


class SuggestedQuestionsResult(BaseModel):
    """Collection of suggested questions for a dataset."""

    dataset_id: str
    questions: list[SuggestedQuestion]


# === Upload Response ===

class UploadResponse(BaseModel):
    """Response after file upload."""
    success: bool
    dataset_id: str
    dataset: DatasetInfo
    message: str


# === Error Response ===

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None


