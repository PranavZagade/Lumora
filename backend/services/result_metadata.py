"""
Result Metadata Builder.

Analyzes query execution results to extract lightweight metadata
for visualization decisions. NO raw data transformation - only metadata inference.

CORE PRINCIPLE: Extract column roles, cardinality, and sparsity from results
without modifying the underlying data.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import re


class ResultMetadata:
    """Metadata extracted from query result."""
    
    def __init__(
        self,
        columns: Dict[str, Dict[str, Any]],
        row_count: int,
        result_type: str
    ):
        self.columns = columns
        self.row_count = row_count
        self.result_type = result_type
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "columns": self.columns,
            "row_count": self.row_count,
            "result_type": self.result_type
        }


def infer_column_role(name: str, values: List[Any]) -> str:
    """
    Infer column role from name and values.
    
    Roles:
    - time: Date/time related columns
    - numeric: Numeric measurement columns
    - categorical: Grouping/dimension columns
    """
    name_lower = name.lower()
    
    # Time indicators in column name
    time_keywords = ["time", "date", "year", "month", "day", "week", "quarter", "period", "timestamp"]
    if any(kw in name_lower for kw in time_keywords):
        return "time"
    
    # Check if values look like time
    if values:
        sample = values[0]
        if isinstance(sample, (datetime,)):
            return "time"
        if isinstance(sample, str):
            # Check for year-like patterns (4 digits)
            if re.match(r"^\d{4}$", str(sample)):
                return "time"
            # Check for date patterns
            if re.match(r"^\d{4}-\d{2}", str(sample)):
                return "time"
    
    # Numeric indicators
    numeric_keywords = ["count", "sum", "avg", "average", "total", "amount", "value", "price", "quantity", "num", "number"]
    if any(kw in name_lower for kw in numeric_keywords):
        return "numeric"
    
    # Check if values are numeric
    if values:
        sample = values[0]
        if isinstance(sample, (int, float)) and not isinstance(sample, bool):
            return "numeric"
    
    # Default to categorical
    return "categorical"


def calculate_cardinality(values: List[Any]) -> int:
    """Calculate unique value count."""
    try:
        return len(set(str(v) for v in values if v is not None))
    except (TypeError, ValueError):
        return len(values)


def calculate_sparsity(values: List[Any]) -> float:
    """Calculate null/missing percentage (0.0 to 1.0)."""
    if not values:
        return 0.0
    null_count = sum(1 for v in values if v is None or v == "" or (isinstance(v, float) and v != v))  # NaN check
    return null_count / len(values)


def get_numeric_stats(values: List[Any]) -> Dict[str, Optional[float]]:
    """Get min/max for numeric values."""
    numeric_values = []
    for v in values:
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if v == v:  # NaN check
                numeric_values.append(v)
    
    if not numeric_values:
        return {"min": None, "max": None}
    
    return {
        "min": min(numeric_values),
        "max": max(numeric_values)
    }


def build_result_metadata(result_data: Dict[str, Any]) -> ResultMetadata:
    """
    Build metadata from query execution result.
    
    Supports result types: time_series, ranking, breakdown, table
    """
    result_type = result_data.get("type", "unknown")
    columns: Dict[str, Dict[str, Any]] = {}
    row_count = 0
    
    if result_type == "scalar":
        # Scalar results don't need visualization metadata
        return ResultMetadata(columns={}, row_count=1, result_type=result_type)
    
    elif result_type == "empty":
        return ResultMetadata(columns={}, row_count=0, result_type=result_type)
    
    elif result_type in ["time_series", "ranking", "breakdown"]:
        data = result_data.get("data", [])
        row_count = len(data)
        
        if not data:
            return ResultMetadata(columns={}, row_count=0, result_type=result_type)
        
        # Extract column info from first row keys
        sample_row = data[0]
        
        for key in sample_row.keys():
            values = [row.get(key) for row in data]
            role = infer_column_role(key, values)
            cardinality = calculate_cardinality(values)
            sparsity = calculate_sparsity(values)
            
            col_meta = {
                "role": role,
                "cardinality": cardinality,
                "sparsity": sparsity
            }
            
            # Add numeric stats if applicable
            if role == "numeric":
                stats = get_numeric_stats(values)
                col_meta.update(stats)
            
            columns[key] = col_meta
    
    elif result_type == "table":
        data = result_data.get("data", [])
        row_count = len(data)
        
        if not data:
            return ResultMetadata(columns={}, row_count=0, result_type=result_type)
        
        # Get columns from first row
        sample_row = data[0]
        
        for key in sample_row.keys():
            values = [row.get(key) for row in data]
            role = infer_column_role(key, values)
            cardinality = calculate_cardinality(values)
            sparsity = calculate_sparsity(values)
            
            col_meta = {
                "role": role,
                "cardinality": cardinality,
                "sparsity": sparsity
            }
            
            if role == "numeric":
                stats = get_numeric_stats(values)
                col_meta.update(stats)
            
            columns[key] = col_meta
    
    return ResultMetadata(
        columns=columns,
        row_count=row_count,
        result_type=result_type
    )
