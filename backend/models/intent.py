"""
Strict Intent Schema for Chat Execution Engine.

CORE PRINCIPLE: All intents reference COLUMN ROLES, not column names.
This ensures rename-invariance and structural analysis.
"""

from typing import Literal, Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator


# === Type Definitions ===

ColumnRole = Literal["identifier", "timestamp", "metric", "dimension"]
Aggregation = Literal["sum", "mean", "count", "min", "max", "median", "std"]
TimeGranularity = Literal["day", "week", "month", "quarter", "year"]
VisualizationType = Literal["line", "bar", "table", "none"]
IntentType = Literal["dataset_overview", "aggregate", "rank", "compare", "clarification_required"]


# === Base Intent Model ===

class BaseIntent(BaseModel):
    """Base intent with common fields."""
    type: IntentType
    visualization: VisualizationType = Field(default="none", description="Requested visualization type")
    
    class Config:
        extra = "forbid"  # Reject any extra fields


# === Aggregate Intent ===

class AggregateIntent(BaseIntent):
    """Aggregate metrics over time or dimensions."""
    type: Literal["aggregate"] = "aggregate"
    
    # Required: What to aggregate (optional for count aggregation)
    metric_role: Optional[ColumnRole] = Field(
        default=None,
        description="Role of column to aggregate (must be 'metric' for sum/mean, optional for count)"
    )
    
    # Optional: Group by
    group_by_role: Optional[ColumnRole] = Field(
        default=None,
        description="Role to group by (timestamp, dimension, or None for total)"
    )
    
    # Aggregation function
    aggregation: Aggregation = Field(default="sum", description="Aggregation function to apply")
    
    # Post-processing (e.g., find min/max of aggregated results)
    post_process: Optional[Literal["min", "max"]] = Field(
        default=None,
        description="Post-process aggregated results (e.g., find min/max)"
    )
    
    # Time-specific options
    time_granularity: Optional[TimeGranularity] = Field(
        default=None,
        description="Time granularity if grouping by timestamp"
    )
    
    @field_validator("metric_role", mode="before")
    @classmethod
    def validate_metric_role_before(cls, v: Optional[ColumnRole]) -> Optional[ColumnRole]:
        """Basic validation - check it's valid if provided."""
        if v is not None and v != "metric":
            raise ValueError("metric_role must be 'metric' or None")
        return v
    
    @field_validator("metric_role")
    @classmethod
    def validate_metric_role(cls, v: Optional[ColumnRole], info) -> Optional[ColumnRole]:
        """Ensure metric_role matches aggregation requirements."""
        # Get aggregation from the model instance (after all fields are set)
        if hasattr(info, "data"):
            agg = info.data.get("aggregation")
        elif hasattr(info, "instance"):
            agg = info.instance.aggregation if hasattr(info.instance, "aggregation") else None
        else:
            # Fallback: try to get from context
            agg = getattr(info, "aggregation", None)
        
        # If we can't determine aggregation yet, skip validation (will be checked in model_validator)
        if agg is None:
            return v
        
        # Count aggregation MUST have null metric_role
        if agg == "count" and v is not None:
            raise ValueError("metric_role must be null for count aggregation")
        # Other aggregations MUST have metric_role
        if agg in ["sum", "mean", "min", "max", "median", "std"] and v is None:
            raise ValueError(f"metric_role is required for aggregation '{agg}'")
        return v
    
    @classmethod
    def model_validator(cls, values):
        """Final validation after all fields are set."""
        if isinstance(values, dict):
            agg = values.get("aggregation", "sum")
            metric_role = values.get("metric_role")
            
            # Count aggregation MUST have null metric_role
            if agg == "count" and metric_role is not None:
                raise ValueError("metric_role must be null for count aggregation")
            # Other aggregations MUST have metric_role
            if agg in ["sum", "mean", "min", "max", "median", "std"] and metric_role is None:
                raise ValueError(f"metric_role is required for aggregation '{agg}'")
        
        return values
    
    @field_validator("time_granularity")
    @classmethod
    def validate_time_granularity(cls, v: Optional[TimeGranularity], info) -> Optional[TimeGranularity]:
        """Ensure time_granularity is only set when grouping by timestamp."""
        if v is not None:
            # In Pydantic v2, access via info.data
            if hasattr(info, "data"):
                group_by = info.data.get("group_by_role")
            else:
                # Fallback for Pydantic v1
                group_by = getattr(info, "group_by_role", None)
            if group_by != "timestamp":
                raise ValueError("time_granularity can only be set when group_by_role is 'timestamp'")
        return v


# === Compare Intent ===

class CompareIntent(BaseIntent):
    """Compare metrics across dimensions."""
    type: Literal["compare"] = "compare"
    
    metric_role: ColumnRole = Field(description="Role of column to compare (must be 'metric')")
    dimension_role: ColumnRole = Field(description="Role to compare across (must be 'dimension')")
    aggregation: Aggregation = Field(default="sum", description="Aggregation function")
    limit: Optional[int] = Field(default=10, description="Limit number of results")
    
    @field_validator("metric_role")
    @classmethod
    def validate_metric_role(cls, v: ColumnRole) -> ColumnRole:
        if v != "metric":
            raise ValueError("metric_role must be 'metric'")
        return v
    
    @field_validator("dimension_role")
    @classmethod
    def validate_dimension_role(cls, v: ColumnRole) -> ColumnRole:
        if v != "dimension":
            raise ValueError("dimension_role must be 'dimension'")
        return v


# === Rank Intent ===

class RankIntent(BaseIntent):
    """Rank by metric value (can rank dimensions or timestamps)."""
    type: Literal["rank"] = "rank"
    
    # Optional: metric to rank by (null for count-based ranking)
    metric_role: Optional[ColumnRole] = Field(
        default=None,
        description="Role of column to rank by (must be 'metric' for sum/mean, null for count)"
    )
    
    # Required: what to rank (dimension or timestamp)
    group_by_role: ColumnRole = Field(
        description="Role to rank (must be 'dimension' or 'timestamp')"
    )
    
    aggregation: Aggregation = Field(default="count", description="Aggregation function")
    order: Literal["asc", "desc"] = Field(default="desc", description="Sort order")
    limit: Optional[int] = Field(default=10, description="Limit number of results")
    
    # Time-specific options (only if group_by_role is timestamp)
    time_granularity: Optional[TimeGranularity] = Field(
        default=None,
        description="Time granularity if grouping by timestamp"
    )
    
    @field_validator("metric_role", mode="before")
    @classmethod
    def validate_metric_role_before(cls, v: Optional[ColumnRole]) -> Optional[ColumnRole]:
        """Basic validation - check it's valid if provided."""
        if v is not None and v != "metric":
            raise ValueError("metric_role must be 'metric' or None")
        return v
    
    @classmethod
    def model_validator(cls, values):
        """Final validation after all fields are set."""
        if isinstance(values, dict):
            agg = values.get("aggregation", "count")
            metric_role = values.get("metric_role")
            
            # Count aggregation MUST have null metric_role
            if agg == "count" and metric_role is not None:
                raise ValueError("metric_role must be null for count aggregation")
            # Other aggregations MUST have metric_role
            if agg in ["sum", "mean", "min", "max", "median", "std"] and metric_role is None:
                raise ValueError(f"metric_role is required for aggregation '{agg}'")
        
        return values
    
    @field_validator("group_by_role")
    @classmethod
    def validate_group_by_role(cls, v: ColumnRole) -> ColumnRole:
        """Ensure group_by_role is dimension or timestamp."""
        if v not in ["dimension", "timestamp"]:
            raise ValueError("group_by_role must be 'dimension' or 'timestamp'")
        return v
    
    @field_validator("time_granularity")
    @classmethod
    def validate_time_granularity(cls, v: Optional[TimeGranularity], info) -> Optional[TimeGranularity]:
        """Ensure time_granularity is only set when grouping by timestamp."""
        if v is not None:
            if hasattr(info, "data"):
                group_by = info.data.get("group_by_role")
            else:
                group_by = getattr(info, "group_by_role", None)
            if group_by != "timestamp":
                raise ValueError("time_granularity can only be set when group_by_role is 'timestamp'")
        return v


# === Dataset Overview Intent ===

class DatasetOverviewIntent(BaseIntent):
    """Questions about dataset structure (rows, columns)."""
    type: Literal["dataset_overview"] = "dataset_overview"
    
    # No additional fields needed - just returns row/column counts
    # Validation: must NOT have group_by_role
    @field_validator("group_by_role", check_fields=False)
    @classmethod
    def validate_no_group_by(cls, v):
        """Dataset overview must not have group_by_role."""
        if v is not None:
            raise ValueError("dataset_overview intent cannot have group_by_role")
        return v


# === Clarification Required Intent ===

class ClarificationRequiredIntent(BaseIntent):
    """Intent cannot be determined - user needs to clarify."""
    type: Literal["clarification_required"] = "clarification_required"
    
    message: str = Field(
        default="Please clarify what you want to analyze.",
        description="Message to show user asking for clarification"
    )


# === Union Type for All Intents ===

Intent = Union[
    DatasetOverviewIntent,
    AggregateIntent,
    RankIntent,
    CompareIntent,
    ClarificationRequiredIntent
]


# === Intent Request/Response Models ===

class IntentRequest(BaseModel):
    """Request to generate an intent from a question."""
    question: str = Field(description="User's natural language question")
    available_roles: List[ColumnRole] = Field(description="Available column roles in the dataset")
    role_counts: Dict[ColumnRole, int] = Field(
        default_factory=dict,
        description="Count of columns per role"
    )
    total_rows: int = Field(
        default=0,
        description="Total number of rows in the dataset"
    )


class IntentResponse(BaseModel):
    """Generated intent from LLM."""
    intent: Dict[str, Any] = Field(description="Validated intent JSON")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score")


class ExecutionResult(BaseModel):
    """Result of executing an intent."""
    dataset_id: str
    intent_type: IntentType
    data: Dict[str, Any] = Field(description="Result data (table, scalar, etc.)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")
    explanation: Optional[str] = Field(default=None, description="AI-generated explanation (optional)")

