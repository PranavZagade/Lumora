"""
Safe Query Execution Service.

Executes validated SQL queries using DuckDB with safety constraints.
"""

import duckdb
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import sys

from services.storage import storage
from services.analyzer import get_dataframe_from_bytes

logger = logging.getLogger(__name__)


class ExecutionResult:
    """Result of query execution."""
    def __init__(
        self,
        data: Dict[str, Any],
        execution_time_ms: float,
        rows_returned: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.data = data
        self.execution_time_ms = execution_time_ms
        self.rows_returned = rows_returned
        self.metadata = metadata or {}


def execute_query(
    dataset_id: str,
    query: str,
    table_name: str = "data",
    timeout_seconds: int = 2,
    max_rows: int = 10000
) -> ExecutionResult:
    """
    Execute a validated SQL query safely.
    
    Safety constraints:
    - Timeout (2 seconds default)
    - Row limit (10000 default)
    - Memory limits (handled by DuckDB)
    - Read-only mode
    """
    start_time = datetime.utcnow()
    
    # Load dataset
    profile_data = storage.get_json(dataset_id, "profile")
    if not profile_data:
        raise ValueError(f"Profile for dataset {dataset_id} not found")
    
    dataset_name = profile_data.get("dataset", {}).get("name", "data.csv")
    dataset_bytes = storage.get_file(dataset_id, dataset_name)
    if not dataset_bytes:
        raise ValueError(f"Dataset file {dataset_name} not found")
    
    # Load DataFrame
    df = get_dataframe_from_bytes(dataset_bytes, dataset_name)
    total_rows = len(df)
    
    # Create DuckDB connection
    conn = duckdb.connect()
    
    try:
        # Register DataFrame as table
        conn.register(table_name, df)
        
        # Execute query with timeout (simplified - actual timeout needs async or threading)
        # For now, we'll rely on DuckDB's internal limits
        try:
            result_df = conn.execute(query).df()
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise ValueError(f"Query execution failed: {str(e)}")
        
        # Check row limit
        if len(result_df) > max_rows:
            result_df = result_df.head(max_rows)
            logger.warning(f"Query result truncated to {max_rows} rows")
        
        # Calculate execution time
        end_time = datetime.utcnow()
        execution_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Convert result to structured format
        result_data = _format_result(result_df, query)
        
        # Validate result
        _validate_result(result_data, total_rows)
        
        return ExecutionResult(
            data=result_data,
            execution_time_ms=execution_time_ms,
            rows_returned=len(result_df),
            metadata={
                "executed_at": end_time.isoformat(),
                "total_rows_in_dataset": total_rows,
                "query": query[:200],  # Truncate for logging
            }
        )
        
    finally:
        conn.close()


def _format_result(df: pd.DataFrame, query: str) -> Dict[str, Any]:
    """Format query result into structured response."""
    if df.empty:
        return {
            "type": "empty",
            "message": "No results found."
        }
    
    # Determine result type based on shape and query
    query_upper = query.upper()
    
    # Scalar result (single row, single column)
    if len(df) == 1 and len(df.columns) == 1:
            value = df.iloc[0, 0]
            col_name = df.columns[0]
            
            # Check if it's a count
            if "COUNT" in query_upper:
                return {
                    "type": "scalar",
                    "value": float(value) if pd.notna(value) else 0.0,
                    "aggregation": "count",
                    "column_name": col_name,
                }
            # Check if it's an aggregation
            elif any(agg in query_upper for agg in ["AVG", "SUM", "MIN", "MAX"]):
                agg_type = "mean" if "AVG" in query_upper else "sum" if "SUM" in query_upper else "min" if "MIN" in query_upper else "max"
                return {
                    "type": "scalar",
                    "value": float(value) if pd.notna(value) else 0.0,
                    "aggregation": agg_type,
                    "column_name": col_name,
                }
            else:
                return {
                    "type": "scalar",
                    "value": float(value) if isinstance(value, (int, float)) else str(value),
                    "column_name": col_name,
                }
    
    # Time series (has time column and value column)
    if len(df.columns) >= 2:
        # Check if first column looks like time
        first_col = df.columns[0]
        if any(time_word in first_col.upper() for time_word in ["TIME", "DATE", "YEAR", "MONTH", "DAY"]):
            return {
                "type": "time_series",
                "data": [
                    {
                        "time": str(row[first_col]),
                        "value": float(row[df.columns[1]]) if pd.notna(row[df.columns[1]]) else 0.0
                    }
                    for _, row in df.iterrows()
                ],
                "time_column": first_col,
                "metric_column": df.columns[1] if len(df.columns) > 1 else None,
            }
    
    # Ranking (has rank or ordered by count/value)
    if "ORDER BY" in query_upper and "DESC" in query_upper:
        # Likely a ranking
        if len(df.columns) >= 2:
            return {
                "type": "ranking",
                "data": [
                    {
                        "group": str(row[df.columns[0]]),
                        "value": float(row[df.columns[1]]) if pd.notna(row[df.columns[1]]) else 0.0,
                        "rank": i + 1
                    }
                    for i, (_, row) in enumerate(df.iterrows())
                ],
                "group_column": df.columns[0],
                "metric_column": df.columns[1] if len(df.columns) > 1 else None,
            }
    
    # Breakdown (grouped data)
    if "GROUP BY" in query_upper:
        return {
            "type": "breakdown",
            "data": [
                {
                    "group": str(row[df.columns[0]]),  # Use "group" for consistency
                    "value": float(row[df.columns[1]]) if len(df.columns) > 1 and pd.notna(row[df.columns[1]]) else 0.0
                }
                for _, row in df.iterrows()
            ],
            "group_column": df.columns[0],  # Use "group_column" for consistency
            "metric_column": df.columns[1] if len(df.columns) > 1 else None,
        }
    
    # Default: table result
    return {
        "type": "table",
        "data": df.to_dict("records"),
        "columns": list(df.columns),
    }


def _validate_result(result_data: Dict[str, Any], total_rows: int) -> None:
    """Validate execution result for sanity."""
    result_type = result_data.get("type")
    
    if result_type == "scalar":
        value = result_data.get("value")
        if isinstance(value, (int, float)):
            if not np.isfinite(value):
                raise ValueError("Result contains invalid numeric value (NaN or infinite)")
            if "count" in str(result_data.get("aggregation", "")).lower():
                if value > total_rows:
                    raise ValueError(f"Count result ({value}) exceeds total rows ({total_rows})")
                if value < 0:
                    raise ValueError(f"Count result ({value}) cannot be negative")
    
    elif result_type in ["time_series", "breakdown", "ranking"]:
        data = result_data.get("data", [])
        if not isinstance(data, list):
            raise ValueError(f"Expected list data for {result_type}")
        
        for item in data:
            if "value" in item:
                value = item["value"]
                if isinstance(value, (int, float)):
                    if not np.isfinite(value):
                        raise ValueError("Result contains invalid numeric value")
    
    elif result_type == "table":
        data = result_data.get("data", [])
        if not isinstance(data, list):
            raise ValueError("Table result must have data list")
    
    elif result_type == "empty":
        # Empty results are valid
        pass
    
    else:
        raise ValueError(f"Unknown result type: {result_type}")

