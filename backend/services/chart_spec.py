"""
Chart Specification Generator.

Generates strict chart specification JSON that describes how to render
visualization without transforming the underlying data.

CORE PRINCIPLE: 
- No data transformation - pass-through only
- Axis safety guards for dense labels
- Deterministic spec generation
"""

from typing import Dict, Any, List, Optional
from services.result_metadata import ResultMetadata
from services.visualization_eligibility import EligibilityResult
from services.chart_intent import select_chart_type, get_intent_metadata


# Safety thresholds for readable axes
MAX_X_TICKS = 12
MAX_Y_TICKS = 8
MAX_LABEL_LENGTH = 15
LABEL_ROTATION_THRESHOLD = 8  # Rotate labels if more than this many items


class ChartSpec:
    """Chart specification for frontend rendering."""
    
    def __init__(
        self,
        chart_type: str,
        intent: str,
        title: str,
        x_axis: Dict[str, Any],
        y_axis: Dict[str, Any],
        data: List[Dict[str, Any]],
        ui_hints: Dict[str, Any],
        fallback_reason: Optional[str] = None
    ):
        self.chart_type = chart_type
        self.intent = intent
        self.title = title
        self.x_axis = x_axis
        self.y_axis = y_axis
        self.data = data
        self.ui_hints = ui_hints
        self.fallback_reason = fallback_reason
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "chart_type": self.chart_type,
            "intent": self.intent,
            "title": self.title,
            "x_axis": self.x_axis,
            "y_axis": self.y_axis,
            "data": self.data,
            "ui_hints": self.ui_hints
        }
        if self.fallback_reason:
            result["fallback_reason"] = self.fallback_reason
        return result


def _truncate_label(label: str, max_length: int = MAX_LABEL_LENGTH) -> str:
    """Truncate label with ellipsis if too long."""
    if len(label) <= max_length:
        return label
    return label[:max_length - 1] + "…"


def _calculate_tick_sampling(data_count: int, max_ticks: int) -> int:
    """Calculate tick interval for sampling."""
    if data_count <= max_ticks:
        return 1  # Show all
    return max(1, data_count // max_ticks)


def _detect_long_labels(data: List[Dict[str, Any]], label_field: str) -> bool:
    """Check if any labels exceed threshold length."""
    for item in data:
        label = str(item.get(label_field, ""))
        if len(label) > MAX_LABEL_LENGTH:
            return True
    return False


def _generate_title(
    result_data: Dict[str, Any],
    metadata: ResultMetadata,
    shape: str
) -> str:
    """Generate descriptive chart title."""
    columns = metadata.columns
    
    # Get field names from result
    if shape == "time_series":
        time_col = result_data.get("time_column", "Time")
        metric_col = result_data.get("metric_column", "Value")
        return f"{metric_col.replace('_', ' ').title()} by {time_col.replace('_', ' ').title()}"
    
    elif shape == "ranking":
        group_col = result_data.get("group_column", "Category")
        metric_col = result_data.get("metric_column", "Value")
        return f"Top {group_col.replace('_', ' ').title()} by {metric_col.replace('_', ' ').title()}"
    
    elif shape == "breakdown":
        group_col = result_data.get("group_column", result_data.get("dimension_column", "Category"))
        metric_col = result_data.get("metric_column", "Value")
        return f"{metric_col.replace('_', ' ').title()} by {group_col.replace('_', ' ').title()}"
    
    return "Data Visualization"


def generate_chart_spec(
    result_data: Dict[str, Any],
    metadata: ResultMetadata,
    eligibility: EligibilityResult
) -> Optional[ChartSpec]:
    """
    Generate chart specification from query result.
    
    Returns ChartSpec or None if not visualizable.
    """
    if not eligibility.eligible:
        return None
    
    shape = eligibility.shape
    data = result_data.get("data", [])
    row_count = metadata.row_count
    
    if not data:
        return None
    
    # Check for long labels
    sample_row = data[0]
    label_fields = [k for k in sample_row.keys() if k not in ["value", "rank"]]
    label_field = label_fields[0] if label_fields else "group"
    has_long_labels = _detect_long_labels(data, label_field)
    
    # Select chart type
    chart_type = select_chart_type(shape, row_count, has_long_labels)
    
    # Get intent metadata
    intent_meta = get_intent_metadata(shape)
    
    # Generate title
    title = _generate_title(result_data, metadata, shape)
    
    # Determine axis configuration based on result type and chart type
    x_axis: Dict[str, Any] = {}
    y_axis: Dict[str, Any] = {}
    
    if shape == "time_series":
        time_col = result_data.get("time_column", "time")
        metric_col = result_data.get("metric_column", "value")
        
        x_axis = {
            "field": "time",
            "label": time_col.replace("_", " ").title(),
            "type": "time"
        }
        y_axis = {
            "field": "value",
            "label": metric_col.replace("_", " ").title(),
            "type": "numeric"
        }
    
    elif shape == "ranking":
        group_col = result_data.get("group_column", "group")
        metric_col = result_data.get("metric_column", "value")
        
        if chart_type == "horizontal_bar":
            # Swap axes for horizontal bar
            x_axis = {
                "field": "value",
                "label": metric_col.replace("_", " ").title(),
                "type": "numeric"
            }
            y_axis = {
                "field": "group",
                "label": group_col.replace("_", " ").title(),
                "type": "categorical"
            }
        else:
            x_axis = {
                "field": "group",
                "label": group_col.replace("_", " ").title(),
                "type": "categorical"
            }
            y_axis = {
                "field": "value",
                "label": metric_col.replace("_", " ").title(),
                "type": "numeric"
            }
    
    elif shape == "breakdown":
        # Handle both "group" and "dimension" field names
        group_col = result_data.get("group_column", result_data.get("dimension_column", "group"))
        metric_col = result_data.get("metric_column", "value")
        
        # Determine field name in data
        sample = data[0]
        group_field = "group" if "group" in sample else "dimension"
        
        if chart_type == "horizontal_bar":
            x_axis = {
                "field": "value",
                "label": metric_col.replace("_", " ").title(),
                "type": "numeric"
            }
            y_axis = {
                "field": group_field,
                "label": group_col.replace("_", " ").title(),
                "type": "categorical"
            }
        elif chart_type == "donut":
            # Donut doesn't have traditional axes
            x_axis = {
                "field": group_field,
                "label": group_col.replace("_", " ").title(),
                "type": "categorical"
            }
            y_axis = {
                "field": "value",
                "label": metric_col.replace("_", " ").title(),
                "type": "numeric"
            }
        else:
            x_axis = {
                "field": group_field,
                "label": group_col.replace("_", " ").title(),
                "type": "categorical"
            }
            y_axis = {
                "field": "value",
                "label": metric_col.replace("_", " ").title(),
                "type": "numeric"
            }
    
    # Calculate UI hints for axis safety
    tick_interval = _calculate_tick_sampling(row_count, MAX_X_TICKS)
    should_rotate = row_count > LABEL_ROTATION_THRESHOLD and chart_type not in ["horizontal_bar", "donut"]
    
    ui_hints = {
        "max_ticks": MAX_X_TICKS,
        "tick_interval": tick_interval,
        "label_rotation": -45 if should_rotate else 0,
        "truncate_labels": has_long_labels,
        "max_label_length": MAX_LABEL_LENGTH,
        "show_legend": chart_type == "donut",
        "show_grid": chart_type in ["line", "area", "bar", "horizontal_bar"],
        "animate": True
    }
    
    return ChartSpec(
        chart_type=chart_type,
        intent=intent_meta["intent"],
        title=title,
        x_axis=x_axis,
        y_axis=y_axis,
        data=data,  # Pass-through, no transformation
        ui_hints=ui_hints
    )
