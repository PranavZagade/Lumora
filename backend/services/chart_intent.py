"""
Chart Intent and Type Mapping.

Maps visualization shapes to chart intents and allowed chart types.
Provides deterministic rules for chart selection.

CORE PRINCIPLE: Each shape maps to a specific intent and limited chart types.
No AI/LLM involvement in chart type selection.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ChartIntent:
    """Chart intent with allowed types."""
    intent: str
    allowed_types: List[str]
    preferred_type: str
    description: str


# Intent taxonomy mapping
INTENT_MAP: Dict[str, ChartIntent] = {
    "time_series": ChartIntent(
        intent="trend",
        allowed_types=["line", "area"],
        preferred_type="line",
        description="Show change over time"
    ),
    "ranking": ChartIntent(
        intent="ranking",
        allowed_types=["horizontal_bar", "bar"],
        preferred_type="horizontal_bar",
        description="Compare items by value (sorted)"
    ),
    "breakdown": ChartIntent(
        intent="composition",
        allowed_types=["bar", "horizontal_bar", "donut"],
        preferred_type="bar",
        description="Show distribution across categories"
    ),
    "distribution": ChartIntent(
        intent="distribution",
        allowed_types=["histogram", "bar"],
        preferred_type="bar",
        description="Show value distribution"
    ),
}


# Thresholds for chart type switching
MAX_ITEMS_FOR_DONUT = 8
MAX_ITEMS_FOR_VERTICAL_BAR = 12
MIN_ITEMS_FOR_HORIZONTAL = 5


def get_chart_intent(shape: str) -> Optional[ChartIntent]:
    """Get chart intent for a visualization shape."""
    return INTENT_MAP.get(shape)


def select_chart_type(
    shape: str,
    row_count: int,
    has_long_labels: bool = False
) -> str:
    """
    Select the best chart type based on shape and data characteristics.
    
    Rules:
    - time_series: Always line (or area for emphasis)
    - ranking: horizontal_bar for readability
    - breakdown: bar for <=12 items, donut for <=8 items with single metric
    - Long labels: Prefer horizontal bar for readability
    """
    intent = get_chart_intent(shape)
    
    if not intent:
        return "bar"  # Safe default
    
    # Time series always gets line chart
    if shape == "time_series":
        return "line"
    
    # Ranking always gets horizontal bar for readability
    if shape == "ranking":
        return "horizontal_bar"
    
    # Breakdown depends on item count
    if shape == "breakdown":
        # Many items or long labels → horizontal bar
        if row_count > MAX_ITEMS_FOR_VERTICAL_BAR or has_long_labels:
            return "horizontal_bar"
        
        # Few items could use donut
        if row_count <= MAX_ITEMS_FOR_DONUT:
            # Could return "donut" here, but bar is safer for accuracy
            return "bar"
        
        return "bar"
    
    # Distribution
    if shape == "distribution":
        return "bar"
    
    return intent.preferred_type


def get_intent_metadata(shape: str) -> Dict[str, Any]:
    """Get intent metadata for chart spec."""
    intent = get_chart_intent(shape)
    
    if not intent:
        return {
            "intent": "unknown",
            "intent_description": "Unknown visualization intent"
        }
    
    return {
        "intent": intent.intent,
        "intent_description": intent.description
    }
