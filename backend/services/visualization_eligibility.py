"""
Visualization Eligibility Gate.

Deterministic gate that decides if a query result is suitable for visualization.
Returns eligibility status and inferred visualization shape.

CORE PRINCIPLE: Strict, deterministic rules - no AI/LLM involvement.
"""

from typing import Dict, Any, Optional
from services.result_metadata import ResultMetadata


# Thresholds for eligibility decisions
MIN_DATA_POINTS = 2
MAX_RANKING_ITEMS = 30  # Horizontal bars can handle up to 30 items
MAX_BREAKDOWN_ITEMS = 30
MAX_TIME_SERIES_ROWS = 365  # Line charts can handle more points (up to 1 year of daily data)
MAX_CHART_ROWS = 100  # Default for bar/other charts
MIN_CARDINALITY_FOR_CHART = 2


class EligibilityResult:
    """Result of eligibility check."""
    
    def __init__(
        self,
        eligible: bool,
        reason: Optional[str] = None,
        shape: Optional[str] = None
    ):
        self.eligible = eligible
        self.reason = reason
        self.shape = shape
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"eligible": self.eligible}
        if self.reason:
            result["reason"] = self.reason
        if self.shape:
            result["shape"] = self.shape
        return result


def check_eligibility(
    result_data: Dict[str, Any],
    metadata: ResultMetadata
) -> EligibilityResult:
    """
    Check if a query result is eligible for visualization.
    
    Returns:
        EligibilityResult with eligible=True and shape, or eligible=False with reason
    
    Shapes:
        - time_series: For trend visualization
        - ranking: For ordered comparison
        - breakdown: For composition/distribution
        - single_value: Not visualizable (scalar)
    """
    result_type = result_data.get("type", "unknown")
    
    # Scalar results are not visualizable
    if result_type == "scalar":
        return EligibilityResult(
            eligible=False,
            reason="Single value results are displayed as text"
        )
    
    # Empty results cannot be visualized
    if result_type == "empty":
        return EligibilityResult(
            eligible=False,
            reason="No data to visualize"
        )
    
    # Check row count
    row_count = metadata.row_count
    
    if row_count < MIN_DATA_POINTS:
        return EligibilityResult(
            eligible=False,
            reason=f"Need at least {MIN_DATA_POINTS} data points for visualization"
        )
    
    # Apply row limit based on result type (time series gets higher limit)
    max_rows = MAX_TIME_SERIES_ROWS if result_type == "time_series" else MAX_CHART_ROWS
    if row_count > max_rows:
        return EligibilityResult(
            eligible=False,
            reason=f"Too many data points ({row_count}) for clear visualization"
        )
    
    # Check for required columns
    columns = metadata.columns
    
    if not columns:
        return EligibilityResult(
            eligible=False,
            reason="No analyzable columns in result"
        )
    
    # Must have at least one numeric column for visualization
    numeric_cols = [name for name, info in columns.items() if info.get("role") == "numeric"]
    
    if not numeric_cols:
        return EligibilityResult(
            eligible=False,
            reason="No numeric data to visualize"
        )
    
    # Determine shape based on result type
    if result_type == "time_series":
        # Check for time column
        time_cols = [name for name, info in columns.items() if info.get("role") == "time"]
        
        if not time_cols:
            # Fallback: treat as breakdown if no time column detected
            return EligibilityResult(
                eligible=True,
                shape="breakdown"
            )
        
        return EligibilityResult(
            eligible=True,
            shape="time_series"
        )
    
    elif result_type == "ranking":
        if row_count > MAX_RANKING_ITEMS:
            return EligibilityResult(
                eligible=False,
                reason=f"Too many items ({row_count}) for ranking chart"
            )
        
        return EligibilityResult(
            eligible=True,
            shape="ranking"
        )
    
    elif result_type == "breakdown":
        if row_count > MAX_BREAKDOWN_ITEMS:
            return EligibilityResult(
                eligible=False,
                reason=f"Too many categories ({row_count}) for breakdown chart"
            )
        
        return EligibilityResult(
            eligible=True,
            shape="breakdown"
        )
    
    elif result_type == "table":
        # Tables are generally not visualized, but could be if structured right
        # Check if it looks like a 2-column aggregation
        if len(columns) == 2:
            cat_cols = [n for n, i in columns.items() if i.get("role") in ["categorical", "time"]]
            num_cols = [n for n, i in columns.items() if i.get("role") == "numeric"]
            
            if cat_cols and num_cols and row_count <= MAX_BREAKDOWN_ITEMS:
                return EligibilityResult(
                    eligible=True,
                    shape="breakdown"
                )
        
        return EligibilityResult(
            eligible=False,
            reason="Table results are displayed as text"
        )
    
    # Unknown result type
    return EligibilityResult(
        eligible=False,
        reason=f"Unsupported result type: {result_type}"
    )
