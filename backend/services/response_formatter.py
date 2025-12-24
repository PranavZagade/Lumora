"""
Response Formatter Service.

Formats query results into human-readable natural language responses.
CORE PRINCIPLE: Make responses sound human, precise, and context-aware.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


# Aggregation type to language mapping
AGGREGATION_LANGUAGE = {
    "count": "records",
    "COUNT": "records",
    "sum": "total",
    "SUM": "total",
    "avg": "average",
    "AVG": "average",
    "AVERAGE": "average",
    "mean": "average",
    "MEAN": "average",
    "min": "minimum",
    "MIN": "minimum",
    "max": "maximum",
    "MAX": "maximum",
}


def is_metadata_question(question: str) -> bool:
    """
    Check if a question can be answered from dataset metadata.
    
    Metadata questions include:
    - Number of columns
    - Column names
    - Dataset shape (rows, columns)
    """
    question_lower = question.lower()
    
    metadata_patterns = [
        r"how many columns",
        r"number of columns",
        r"what columns",
        r"which columns",
        r"list.*columns",
        r"column names",
        r"dataset shape",
        r"rows.*columns",
        r"dimensions",
    ]
    
    return any(re.search(pattern, question_lower) for pattern in metadata_patterns)


def format_metadata_response(question: str, columns: List[Dict[str, Any]], total_rows: int) -> str:
    """
    Format a metadata-only response.
    """
    question_lower = question.lower()
    
    if "column" in question_lower:
        if "how many" in question_lower or "number" in question_lower:
            return f"This dataset has {len(columns)} columns."
        elif "what" in question_lower or "which" in question_lower or "list" in question_lower:
            column_names = [col.get("name", "") for col in columns if col.get("name")]
            if len(column_names) <= 10:
                names_str = ", ".join(column_names)
                return f"The columns in this dataset are: {names_str}."
            else:
                names_str = ", ".join(column_names[:10])
                return f"This dataset has {len(column_names)} columns. The first 10 are: {names_str}, and {len(column_names) - 10} more."
    
    if "shape" in question_lower or "dimensions" in question_lower:
        return f"This dataset has {total_rows:,} rows and {len(columns)} columns."
    
    return f"This dataset has {total_rows:,} rows and {len(columns)} columns."


def normalize_percentage(value: Any) -> Optional[str]:
    """
    Normalize a value to percentage format if it's in 0-1 range.
    
    Returns:
        - Formatted percentage string if value is 0-1
        - None if not a percentage
    """
    try:
        float_val = float(value)
        # Check if it's in percentage range (0-1)
        if 0 <= float_val <= 1:
            percentage = float_val * 100
            # Round to 1 decimal place
            return f"{percentage:.1f}%"
    except (ValueError, TypeError):
        pass
    
    return None


def format_time_value(value: Any) -> str:
    """
    Format time values for human readability.
    
    - Years → integers (no decimals)
    - Decades → formatted as "2010s", "2000s" (only if explicitly a decade)
    - Avoid float artifacts
    """
    if value is None:
        return "N/A"
    
    try:
        float_val = float(value)
        int_val = int(float_val)
        
        # If it's a year-like value (1900-2100 range)
        if 1900 <= int_val <= 2100:
            # Only format as decade if it's a round decade (ends in 0) AND is a float that suggests decade grouping
            # For now, just return as integer year (decade formatting can be added later if needed)
            return str(int_val)
        
        # For other numeric values, format appropriately
        if float_val == int_val:
            return str(int_val)
        return f"{float_val:.2f}"
    except (ValueError, TypeError):
        return str(value)


def detect_aggregation_type(query: str, result_data: Dict[str, Any]) -> Optional[str]:
    """
    Detect the aggregation type from query or result structure.
    """
    query_upper = query.upper()
    
    # Check query for aggregation keywords
    if "COUNT" in query_upper:
        return "count"
    elif "SUM" in query_upper:
        return "sum"
    elif "AVG" in query_upper or "AVERAGE" in query_upper:
        return "avg"
    elif "MIN" in query_upper:
        return "min"
    elif "MAX" in query_upper:
        return "max"
    
    # Check result structure
    result_type = result_data.get("type")
    if result_type == "scalar":
        # Try to infer from column name
        col_name = result_data.get("column_name", "").upper()
        if "COUNT" in col_name:
            return "count"
        elif "SUM" in col_name or "TOTAL" in col_name:
            return "sum"
        elif "AVG" in col_name or "AVERAGE" in col_name or "MEAN" in col_name:
            return "avg"
        elif "MIN" in col_name:
            return "min"
        elif "MAX" in col_name:
            return "max"
    
    return None


def format_scalar_result(
    value: Any,
    aggregation_type: Optional[str],
    column_name: Optional[str] = None,
    question: Optional[str] = None
) -> str:
    """
    Format a scalar result into natural language.
    """
    # Check if it's a percentage
    pct_str = normalize_percentage(value)
    if pct_str:
        return f"The result is {pct_str}."
    
    # Format the value
    if isinstance(value, (int, float)):
        formatted_value = format_time_value(value) if column_name and "year" in column_name.lower() else value
    else:
        formatted_value = value
    
    # Use aggregation-aware language
    if aggregation_type:
        agg_word = AGGREGATION_LANGUAGE.get(aggregation_type, "value")
        if aggregation_type == "count":
            return f"There are {formatted_value:,} {agg_word}."
        else:
            # For avg, min, max, sum - use appropriate language
            if column_name:
                return f"The {agg_word} {column_name.lower()} is {formatted_value}."
            return f"The {agg_word} is {formatted_value}."
    
    # Fallback
    return f"The result is {formatted_value}."


def is_comparative_question(question: str) -> bool:
    """
    Check if a question uses comparative language.
    """
    question_lower = question.lower()
    comparative_keywords = [
        "higher", "lower", "more", "less", "greater", "smaller",
        "better", "worse", "larger", "bigger", "compare", "comparison"
    ]
    return any(keyword in question_lower for keyword in comparative_keywords)


def format_comparative_result(
    result_data: Dict[str, Any],
    question: str
) -> Optional[str]:
    """
    Format a comparative result into natural language.
    
    Returns None if not a comparative result.
    """
    result_type = result_data.get("type")
    
    if result_type == "breakdown" or result_type == "ranking":
        data = result_data.get("data", [])
        if len(data) < 2:
            return None
        
        # Extract groups and values
        groups = []
        values = []
        for item in data:
            # Support both "group" and "dimension" keys
            group = item.get("group") or item.get("dimension", "")
            value = item.get("value", 0)
            groups.append(group)
            values.append(value)
        
        # Check if question asks for comparison
        question_lower = question.lower()
        
        # Determine comparison direction
        is_higher = any(word in question_lower for word in ["higher", "more", "greater", "larger", "bigger", "maximum", "highest"])
        is_lower = any(word in question_lower for word in ["lower", "less", "smaller", "minimum", "lowest"])
        
        if is_higher or is_lower:
            # Find the group with highest/lowest value
            if is_higher:
                idx = values.index(max(values))
                direction = "higher"
            else:
                idx = values.index(min(values))
                direction = "lower"
            
            target_group = groups[idx]
            target_value = values[idx]
            
            # Format value
            formatted_value = format_time_value(target_value) if isinstance(target_value, (int, float)) else target_value
            
            # Check for ties
            if values.count(values[idx]) > 1:
                tied_groups = [groups[i] for i, v in enumerate(values) if v == values[idx]]
                if len(tied_groups) > 1:
                    groups_str = ", ".join(tied_groups)
                    return f"Multiple groups are tied with the {direction} value ({formatted_value}): {groups_str}."
            
            # Compare with others if there are exactly 2 groups
            if len(groups) == 2:
                other_idx = 1 - idx
                other_group = groups[other_idx]
                other_value = values[other_idx]
                formatted_other = format_time_value(other_value) if isinstance(other_value, (int, float)) else other_value
                
                if is_higher:
                    return f"{target_group} has a higher value ({formatted_value}) than {other_group} ({formatted_other})."
                else:
                    return f"{target_group} has a lower value ({formatted_value}) than {other_group} ({formatted_other})."
            
            # Single group result
            return f"{target_group} has the {direction} value: {formatted_value}."
    
    return None


def format_result(
    result_data: Dict[str, Any],
    query: str,
    question: Optional[str] = None,
    total_rows: Optional[int] = None
) -> str:
    """
    Format a query result into natural language.
    
    This is the main entry point for result formatting.
    """
    result_type = result_data.get("type")
    
    # Handle empty results
    if result_type == "empty" or result_data.get("message"):
        empty_msg = result_data.get("message", "No results found.")
        if question:
            # Try to explain why
            question_lower = question.lower()
            if "where" in question_lower or "with" in question_lower:
                return f"No records match the specified criteria. {empty_msg}"
        return empty_msg
    
    # Handle scalar results
    if result_type == "scalar":
        value = result_data.get("value")
        column_name = result_data.get("column_name")
        aggregation_type = detect_aggregation_type(query, result_data)
        return format_scalar_result(value, aggregation_type, column_name, question)
    
    # Handle comparative results
    if question and is_comparative_question(question):
        comparative_result = format_comparative_result(result_data, question)
        if comparative_result:
            return comparative_result
    
    # Handle ranking results
    if result_type == "ranking":
        data = result_data.get("data", [])
        if not data:
            return "No ranking results found."
        
        # Format top result
        top_item = data[0]
        group = top_item.get("group", "item")
        value = top_item.get("value", 0)
        
        formatted_value = format_time_value(value) if isinstance(value, (int, float)) else value
        
        # Check for ties
        top_value = value
        tied_items = [item for item in data if item.get("value") == top_value]
        if len(tied_items) > 1:
            tied_groups = [item.get("group") for item in tied_items]
            groups_str = ", ".join(tied_groups[:3])
            if len(tied_groups) > 3:
                groups_str += f", and {len(tied_groups) - 3} more"
            return f"Multiple items are tied for the top position ({formatted_value}): {groups_str}."
        
        return f"The top result is {group} with a value of {formatted_value}."
    
    # Handle breakdown results
    if result_type == "breakdown":
        data = result_data.get("data", [])
        if not data:
            return "No breakdown results found."
        
        if len(data) == 1:
            item = data[0]
            # Support both "group" and "dimension" keys
            group = item.get("group") or item.get("dimension", "item")
            value = item.get("value", 0)
            formatted_value = format_time_value(value) if isinstance(value, (int, float)) else value
            return f"{group} has a value of {formatted_value}."
        
        # Multiple groups - summarize
        total = sum(item.get("value", 0) for item in data)
        top_item = max(data, key=lambda x: x.get("value", 0))
        # Support both "group" and "dimension" keys
        top_group = top_item.get("group") or top_item.get("dimension", "item")
        top_value = top_item.get("value", 0)
        formatted_top = format_time_value(top_value) if isinstance(top_value, (int, float)) else top_value
        
        return f"Results across {len(data)} groups. {top_group} has the highest value: {formatted_top}."
    
    # Handle time series
    if result_type == "time_series":
        data = result_data.get("data", [])
        if not data:
            return "No time series data found."
        
        # Format first and last points
        first = data[0]
        last = data[-1]
        first_time = format_time_value(first.get("time", ""))
        first_value = format_time_value(first.get("value", 0)) if isinstance(first.get("value"), (int, float)) else first.get("value", 0)
        last_time = format_time_value(last.get("time", ""))
        last_value = format_time_value(last.get("value", 0)) if isinstance(last.get("value"), (int, float)) else last.get("value", 0)
        
        return f"Time series shows values from {first_time} ({first_value}) to {last_time} ({last_value})."
    
    # Handle table results
    if result_type == "table":
        data = result_data.get("data", [])
        if not data:
            return "No table results found."
        
        if len(data) == 1:
            return f"Found 1 result: {data[0]}."
        
        return f"Found {len(data)} results."
    
    # Fallback
    return "Query executed successfully."

