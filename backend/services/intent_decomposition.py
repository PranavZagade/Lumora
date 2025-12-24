"""
Intent Decomposition Service.

Decomposes user questions into structured components before SQL generation.
CORE PRINCIPLE: Understand intent structure, not semantics.
"""

import re
from typing import Dict, List, Set, Optional, Literal, Tuple, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class IntentComponents:
    """Decomposed intent components."""
    target_metrics: List[str]  # Concepts or columns being measured
    filters: List[str]  # Filter conditions mentioned
    groupings: List[str]  # Grouping dimensions mentioned
    ordering_terms: List[str]  # Ordering terms (lowest, highest, most, least)
    ordering_target: Optional[str] = None  # What is being ordered
    aggregation_type: Optional[Literal["count", "sum", "avg", "mean", "min", "max"]] = None
    requires_ordering: bool = False  # Whether ordering is required for answer


# Ordering terms that require numeric or ordered data
ORDERING_TERMS = {
    "lowest": ["lowest", "minimum", "min", "smallest", "least"],
    "highest": ["highest", "maximum", "max", "largest", "most"],
    "most": ["most", "highest", "maximum", "greatest"],
    "least": ["least", "lowest", "minimum", "smallest"],
}


def decompose_intent(question: str) -> IntentComponents:
    """
    Decompose a question into structured components.
    
    Returns:
        IntentComponents with target metrics, filters, groupings, ordering terms
    """
    question_lower = question.lower()
    
    # Extract ordering terms
    ordering_terms = []
    ordering_target = None
    requires_ordering = False
    
    for order_type, keywords in ORDERING_TERMS.items():
        for keyword in keywords:
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, question_lower):
                ordering_terms.append(order_type)
                requires_ordering = True
                
                # Try to extract what is being ordered
                # Pattern: "lowest [concept]", "highest [concept]"
                match = re.search(rf"\b{re.escape(keyword)}\s+(\w+)", question_lower)
                if match:
                    ordering_target = match.group(1)
                break
    
    # Extract aggregation type
    aggregation_type = None
    if re.search(r"\b(count|how many|number of)\b", question_lower):
        aggregation_type = "count"
    elif re.search(r"\b(sum|total)\b", question_lower):
        aggregation_type = "sum"
    elif re.search(r"\b(avg|average|mean)\b", question_lower):
        aggregation_type = "avg"
    elif re.search(r"\b(min|minimum|lowest)\b", question_lower):
        aggregation_type = "min"
    elif re.search(r"\b(max|maximum|highest)\b", question_lower):
        aggregation_type = "max"
    
    # Extract grouping dimensions (concepts after "by", "grouped by", "per")
    groupings = []
    grouping_patterns = [
        r"\bby\s+(\w+)",
        r"\bgrouped\s+by\s+(\w+)",
        r"\bper\s+(\w+)",
        r"\bfor\s+each\s+(\w+)",
    ]
    for pattern in grouping_patterns:
        matches = re.findall(pattern, question_lower)
        groupings.extend(matches)
    
    # Extract filters (concepts after "where", "with", "having")
    filters = []
    filter_patterns = [
        r"\bwhere\s+(\w+)",
        r"\bwith\s+(\w+)",
        r"\bhaving\s+(\w+)",
    ]
    for pattern in filter_patterns:
        matches = re.findall(pattern, question_lower)
        filters.extend(matches)
    
    # Extract target metrics (concepts being measured)
    target_metrics = []
    # Pattern: "what is the [aggregation] of [concept]"
    metric_patterns = [
        r"\b(avg|average|sum|total|mean|min|max)\s+(of\s+)?(\w+)",
        r"\bwhat\s+is\s+the\s+(\w+)",
        r"\bthe\s+(\w+)\s+(is|has|equals)",
    ]
    for pattern in metric_patterns:
        matches = re.findall(pattern, question_lower)
        for match in matches:
            if isinstance(match, tuple):
                target_metrics.extend([m for m in match if m and m not in ["of", "is", "has", "equals"]])
            else:
                target_metrics.append(match)
    
    # Remove duplicates
    target_metrics = list(set(target_metrics))
    groupings = list(set(groupings))
    filters = list(set(filters))
    
    logger.info(f"Decomposed intent: metrics={target_metrics}, groupings={groupings}, filters={filters}, ordering={ordering_terms}")
    
    return IntentComponents(
        target_metrics=target_metrics,
        filters=filters,
        groupings=groupings,
        ordering_terms=ordering_terms,
        ordering_target=ordering_target,
        aggregation_type=aggregation_type,
        requires_ordering=requires_ordering,
    )


def check_ordering_validity(
    ordering_target: Optional[str],
    column_info: Dict[str, Any],
    semantic_mappings: Dict[str, str]
) -> Tuple[bool, Optional[str]]:
    """
    Check if ordering can be applied to the target column.
    
    Returns:
        (is_valid, error_message)
    """
    if not ordering_target:
        return True, None
    
    # Map semantic concept to column if needed
    column_name = semantic_mappings.get(ordering_target)
    if not column_name:
        # Try to find column by name
        column_name = ordering_target
    
    if not column_info:
        # Can't validate without column info
        return True, None
    
    col_data = column_info.get(column_name, {})
    col_type = col_data.get("dtype", "text")
    
    # Numeric and datetime columns can always be ordered
    if col_type in ["numeric", "datetime"]:
        return True, None
    
    # Categorical/text columns require explicit ordering
    if col_type in ["categorical", "text"]:
        return False, f"Cannot determine ordering for '{ordering_target}' because it is a categorical/text column. Please define the ordering criteria or use a numeric column."
    
    return True, None

