"""
Intent Execution Service.

CORE PRINCIPLE: All computation happens here, deterministically.
NO AI is used for computation. AI only explains results.

This service:
- Validates intents
- Maps roles → actual columns
- Executes using Pandas
- Returns structured results
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime

from models.intent import (
    Intent,
    AggregateIntent,
    CompareIntent,
    RankIntent,
    DatasetOverviewIntent,
    ClarificationRequiredIntent,
    ExecutionResult,
)
from services.health_check import classify_column_role
from services.storage import storage
from services.analyzer import get_dataframe_from_bytes


# === Deterministic Column Selection ===

def select_best_column_by_role(
    df: pd.DataFrame,
    column_profiles: List[Dict],
    role: str,
    total_rows: int
) -> Optional[str]:
    """
    Select the best column for a given role using deterministic rules.
    
    Selection criteria (in order):
    - For dimensions: lowest null %, moderate cardinality (not 1, not almost row_count)
    - For metrics: lowest null %, non-constant distribution
    - For timestamps: widest date range, fewest invalid dates
    
    Returns the first column after stable sorting, or None if no suitable column.
    """
    candidates = []
    total_rows = len(df)
    
    for col in df.columns:
        col_str = str(col)
        profile = next((p for p in column_profiles if p.get("name") == col_str), None)
        
        if not profile:
            continue
            
        dtype = profile.get("dtype", "text")
        unique_count = profile.get("unique_count", df[col].nunique())
        null_count = profile.get("null_count", df[col].isna().sum())
        detected_role = classify_column_role(dtype, unique_count, total_rows)
        
        if detected_role != role:
            continue
        
        # Skip identifier-like columns (too unique for grouping/aggregation)
        unique_ratio = unique_count / total_rows if total_rows > 0 else 0
        if unique_ratio > 0.9:
            continue
        
        null_pct = (null_count / total_rows * 100) if total_rows > 0 else 0
        
        # Calculate score based on role
        if role == "dimension":
            # Prefer: low null %, moderate cardinality (10-50% unique)
            cardinality_score = 1.0 - abs(unique_ratio - 0.3)  # Prefer ~30% unique
            score = (1.0 - null_pct / 100) * 0.7 + cardinality_score * 0.3
        elif role == "metric":
            # Prefer: low null %, non-constant (has variance)
            try:
                numeric_col = pd.to_numeric(df[col], errors="coerce")
                if numeric_col.notna().sum() > 0:
                    variance = numeric_col.var()
                    variance_score = min(1.0, variance / (numeric_col.max() - numeric_col.min() + 1e-10))
                else:
                    variance_score = 0.0
            except:
                variance_score = 0.0
            score = (1.0 - null_pct / 100) * 0.6 + variance_score * 0.4
        elif role == "timestamp":
            # Prefer: widest date range, fewest invalid dates
            try:
                date_col = pd.to_datetime(df[col], errors="coerce")
                valid_dates = date_col.notna().sum()
                if valid_dates > 0:
                    date_range = (date_col.max() - date_col.min()).days
                    range_score = min(1.0, date_range / 3650)  # Normalize to ~10 years
                    validity_score = valid_dates / total_rows
                    score = range_score * 0.6 + validity_score * 0.4
                else:
                    score = 0.0
            except:
                score = 0.0
        else:
            score = 1.0 - null_pct / 100
        
        candidates.append((col_str, score, null_pct))
    
    if not candidates:
        return None
    
    # Sort by score (descending), then by null_pct (ascending), then by name (stable)
    candidates.sort(key=lambda x: (-x[1], x[2], x[0]))
    
    return candidates[0][0]


def get_columns_by_role(
    df: pd.DataFrame,
    column_profiles: List[Dict],
    role: str
) -> List[str]:
    """Get all column names that match a given role (for compatibility)."""
    matching = []
    total_rows = len(df)
    
    for col in df.columns:
        col_str = str(col)
        profile = next((p for p in column_profiles if p.get("name") == col_str), None)
        
        if profile:
            dtype = profile.get("dtype", "text")
            unique_count = profile.get("unique_count", df[col].nunique())
            detected_role = classify_column_role(dtype, unique_count, total_rows)
            
            if detected_role == role:
                matching.append(col_str)
    
    return matching


# === Execution Functions ===

def execute_aggregate(
    df: pd.DataFrame,
    column_profiles: List[Dict],
    intent: AggregateIntent,
    total_rows: int
) -> Dict[str, Any]:
    """Execute aggregate intent with validation."""
    # Validate intent
    if intent.aggregation in ["sum", "mean", "min", "max", "median", "std"]:
        if intent.metric_role != "metric":
            raise ValueError(f"Aggregation '{intent.aggregation}' requires a metric column")
        metric_col = select_best_column_by_role(df, column_profiles, "metric", total_rows)
        if not metric_col:
            raise ValueError("No suitable metric columns found in dataset")
    else:
        # For "count" aggregation, metric_col can be None
        metric_col = None
    
    # Validate column exists and is accessible
    if metric_col and metric_col not in df.columns:
        raise ValueError(f"Selected metric column '{metric_col}' not found in dataset")
    
    # Prepare aggregation function
    agg_func = intent.aggregation
    
    # Group by logic
    if intent.group_by_role is None:
        # Total aggregation
        if agg_func == "count":
            # Count can work with or without metric column
            if metric_col:
                result = float(df[metric_col].count())
            else:
                result = float(len(df))
        elif metric_col:
            if agg_func == "sum":
                result = float(df[metric_col].sum())
            elif agg_func == "mean":
                result = float(df[metric_col].mean())
            elif agg_func == "min":
                result = float(df[metric_col].min())
            elif agg_func == "max":
                result = float(df[metric_col].max())
            elif agg_func == "median":
                result = float(df[metric_col].median())
            elif agg_func == "std":
                result = float(df[metric_col].std())
            else:
                raise ValueError(f"Unsupported aggregation: {agg_func}")
        else:
            raise ValueError(f"Aggregation '{agg_func}' requires a metric column")
        
        # Post-process if needed
        if intent.post_process == "min":
            result = result  # Already computed min
        elif intent.post_process == "max":
            result = result  # Already computed max
        
        return {
            "type": "scalar",
            "value": result,
            "metric_column": metric_col,
            "aggregation": agg_func,
        }
    
    elif intent.group_by_role == "timestamp":
        # Time-based aggregation - use deterministic selection
        time_col = select_best_column_by_role(df, column_profiles, "timestamp", total_rows)
        if not time_col:
            raise ValueError("No suitable timestamp columns found in dataset")
        
        # Ensure datetime
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
        df = df.dropna(subset=[time_col])
        
        # Apply time granularity
        if intent.time_granularity == "day":
            df["_time_group"] = df[time_col].dt.date
        elif intent.time_granularity == "week":
            df["_time_group"] = df[time_col].dt.to_period("W").astype(str)
        elif intent.time_granularity == "month":
            df["_time_group"] = df[time_col].dt.to_period("M").astype(str)
        elif intent.time_granularity == "quarter":
            df["_time_group"] = df[time_col].dt.to_period("Q").astype(str)
        elif intent.time_granularity == "year":
            df["_time_group"] = df[time_col].dt.year
        else:
            df["_time_group"] = df[time_col].dt.date
        
        # Group and aggregate
        if metric_col:
            grouped = df.groupby("_time_group")[metric_col]
            if agg_func == "sum":
                aggregated = grouped.sum()
            elif agg_func == "mean":
                aggregated = grouped.mean()
            elif agg_func == "count":
                aggregated = grouped.count()
            elif agg_func == "min":
                aggregated = grouped.min()
            elif agg_func == "max":
                aggregated = grouped.max()
            else:
                raise ValueError(f"Unsupported aggregation: {agg_func}")
        else:
            # For count without metric, count rows per time group using size()
            aggregated = df.groupby("_time_group").size()
        
        # Post-process if needed (tie-aware)
        if intent.post_process == "min":
            min_value = aggregated.min()
            # Find ALL groups tied for minimum
            tied_groups = aggregated[aggregated == min_value].index.tolist()
            if len(tied_groups) == 1:
                return {
                    "type": "scalar",
                    "value": float(min_value),
                    "time_period": str(tied_groups[0]),
                    "metric_column": metric_col,
                    "time_column": time_col,
                    "aggregation": agg_func,
                    "tied": False,
                }
            else:
                # Multiple groups tied
                return {
                    "type": "scalar",
                    "value": float(min_value),
                    "time_period": None,
                    "time_periods": [str(g) for g in tied_groups],
                    "metric_column": metric_col,
                    "time_column": time_col,
                    "aggregation": agg_func,
                    "tied": True,
                    "tied_count": len(tied_groups),
                }
        elif intent.post_process == "max":
            max_value = aggregated.max()
            # Find ALL groups tied for maximum
            tied_groups = aggregated[aggregated == max_value].index.tolist()
            if len(tied_groups) == 1:
                return {
                    "type": "scalar",
                    "value": float(max_value),
                    "time_period": str(tied_groups[0]),
                    "metric_column": metric_col,
                    "time_column": time_col,
                    "aggregation": agg_func,
                    "tied": False,
                }
            else:
                # Multiple groups tied
                return {
                    "type": "scalar",
                    "value": float(max_value),
                    "time_period": None,
                    "time_periods": [str(g) for g in tied_groups],
                    "metric_column": metric_col,
                    "time_column": time_col,
                    "aggregation": agg_func,
                    "tied": True,
                    "tied_count": len(tied_groups),
                }
        
        # Return time series
        result_data = [
            {"time": str(k), "value": float(v)}
            for k, v in aggregated.items()
        ]
        
        return {
            "type": "time_series",
            "data": result_data,
            "metric_column": metric_col,
            "time_column": time_col,
            "aggregation": agg_func,
            "granularity": intent.time_granularity or "day",
        }
    
    elif intent.group_by_role == "dimension":
        # Dimension-based aggregation - use deterministic selection
        dim_col = select_best_column_by_role(df, column_profiles, "dimension", total_rows)
        if not dim_col:
            raise ValueError("No suitable dimension columns found in dataset")
        
        # Group and aggregate
        if metric_col:
            grouped = df.groupby(dim_col)[metric_col]
            if agg_func == "sum":
                aggregated = grouped.sum()
            elif agg_func == "mean":
                aggregated = grouped.mean()
            elif agg_func == "count":
                aggregated = grouped.count()
            elif agg_func == "min":
                aggregated = grouped.min()
            elif agg_func == "max":
                aggregated = grouped.max()
            else:
                raise ValueError(f"Unsupported aggregation: {agg_func}")
        else:
            # For count aggregation without metric, count rows per dimension
            aggregated = df.groupby(dim_col).size()
        
        # Post-process if needed (tie-aware)
        if intent.post_process == "min":
            min_value = aggregated.min()
            # Find ALL groups tied for minimum
            tied_groups = aggregated[aggregated == min_value].index.tolist()
            if len(tied_groups) == 1:
                return {
                    "type": "scalar",
                    "value": float(min_value),
                    "dimension_value": str(tied_groups[0]),
                    "metric_column": metric_col,
                    "dimension_column": dim_col,
                    "aggregation": agg_func,
                    "tied": False,
                }
            else:
                # Multiple groups tied
                return {
                    "type": "scalar",
                    "value": float(min_value),
                    "dimension_value": None,
                    "dimension_values": [str(g) for g in tied_groups],
                    "metric_column": metric_col,
                    "dimension_column": dim_col,
                    "aggregation": agg_func,
                    "tied": True,
                    "tied_count": len(tied_groups),
                }
        elif intent.post_process == "max":
            max_value = aggregated.max()
            # Find ALL groups tied for maximum
            tied_groups = aggregated[aggregated == max_value].index.tolist()
            if len(tied_groups) == 1:
                return {
                    "type": "scalar",
                    "value": float(max_value),
                    "dimension_value": str(tied_groups[0]),
                    "metric_column": metric_col,
                    "dimension_column": dim_col,
                    "aggregation": agg_func,
                    "tied": False,
                }
            else:
                # Multiple groups tied
                return {
                    "type": "scalar",
                    "value": float(max_value),
                    "dimension_value": None,
                    "dimension_values": [str(g) for g in tied_groups],
                    "metric_column": metric_col,
                    "dimension_column": dim_col,
                    "aggregation": agg_func,
                    "tied": True,
                    "tied_count": len(tied_groups),
                }
        
        # Return breakdown
        result_data = [
            {"dimension": str(k), "value": float(v)}
            for k, v in aggregated.items()
        ]
        
        return {
            "type": "breakdown",
            "data": result_data,
            "metric_column": metric_col,
            "dimension_column": dim_col,
            "aggregation": agg_func,
        }
    
    else:
        raise ValueError(f"Unsupported group_by_role: {intent.group_by_role}")


def execute_compare(
    df: pd.DataFrame,
    column_profiles: List[Dict],
    intent: CompareIntent,
    total_rows: int
) -> Dict[str, Any]:
    """Execute compare intent with deterministic column selection."""
    metric_col = select_best_column_by_role(df, column_profiles, "metric", total_rows)
    dim_col = select_best_column_by_role(df, column_profiles, "dimension", total_rows)
    
    if not metric_col:
        raise ValueError("No suitable metric columns found")
    if not dim_col:
        raise ValueError("No suitable dimension columns found")
    
    # Group and aggregate
    grouped = df.groupby(dim_col)[metric_col]
    
    if intent.aggregation == "sum":
        aggregated = grouped.sum()
    elif intent.aggregation == "mean":
        aggregated = grouped.mean()
    elif intent.aggregation == "count":
        aggregated = grouped.count()
    elif intent.aggregation == "min":
        aggregated = grouped.min()
    elif intent.aggregation == "max":
        aggregated = grouped.max()
    else:
        raise ValueError(f"Unsupported aggregation: {intent.aggregation}")
    
    # Sort and limit
    sorted_data = aggregated.sort_values(ascending=False)
    if intent.limit:
        sorted_data = sorted_data.head(intent.limit)
    
    result_data = [
        {"dimension": str(k), "value": float(v)}
        for k, v in sorted_data.items()
    ]
    
    return {
        "type": "breakdown",
        "data": result_data,
        "metric_column": metric_col,
        "dimension_column": dim_col,
        "aggregation": intent.aggregation,
    }


def execute_rank(
    df: pd.DataFrame,
    column_profiles: List[Dict],
    intent: RankIntent,
    total_rows: int
) -> Dict[str, Any]:
    """Execute rank intent with deterministic column selection."""
    # Validate: count aggregation must not have metric_role
    if intent.aggregation == "count" and intent.metric_role is not None:
        raise ValueError("count aggregation cannot have metric_role")
    
    # For count aggregation, metric_col is None
    # For other aggregations, metric_col is required
    if intent.aggregation == "count":
        metric_col = None
    else:
        if intent.metric_role != "metric":
            raise ValueError("metric_role must be 'metric' for non-count aggregations")
        metric_col = select_best_column_by_role(df, column_profiles, "metric", total_rows)
        if not metric_col:
            raise ValueError("No suitable metric columns found")
    
    # Select group_by column (dimension or timestamp)
    group_col = select_best_column_by_role(df, column_profiles, intent.group_by_role, total_rows)
    if not group_col:
        raise ValueError(f"No suitable {intent.group_by_role} columns found")
    
    # Handle timestamp grouping with granularity
    if intent.group_by_role == "timestamp":
        # Ensure datetime
        df = df.copy()
        df[group_col] = pd.to_datetime(df[group_col], errors="coerce")
        df = df.dropna(subset=[group_col])
        
        # Apply time granularity
        if intent.time_granularity == "day":
            df["_time_group"] = df[group_col].dt.date
        elif intent.time_granularity == "week":
            df["_time_group"] = df[group_col].dt.to_period("W").astype(str)
        elif intent.time_granularity == "month":
            df["_time_group"] = df[group_col].dt.to_period("M").astype(str)
        elif intent.time_granularity == "quarter":
            df["_time_group"] = df[group_col].dt.to_period("Q").astype(str)
        elif intent.time_granularity == "year":
            df["_time_group"] = df[group_col].dt.year
        else:
            df["_time_group"] = df[group_col].dt.date
        group_col = "_time_group"
    
    # Group and aggregate
    if metric_col:
        grouped = df.groupby(group_col)[metric_col]
        if intent.aggregation == "sum":
            aggregated = grouped.sum()
        elif intent.aggregation == "mean":
            aggregated = grouped.mean()
        elif intent.aggregation == "count":
            aggregated = grouped.count()
        elif intent.aggregation == "min":
            aggregated = grouped.min()
        elif intent.aggregation == "max":
            aggregated = grouped.max()
        else:
            raise ValueError(f"Unsupported aggregation: {intent.aggregation}")
    else:
        # For count without metric, count rows per group
        aggregated = df.groupby(group_col).size()
    
    # Sort
    ascending = intent.order == "asc"
    sorted_data = aggregated.sort_values(ascending=ascending)
    
    if intent.limit:
        sorted_data = sorted_data.head(intent.limit)
    
    # Build result data
    result_data = [
        {
            "group": str(k),
            "value": float(v),
            "rank": i + 1
        }
        for i, (k, v) in enumerate(sorted_data.items())
    ]
    
    return {
        "type": "ranking",
        "data": result_data,
        "metric_column": metric_col,
        "group_column": group_col if intent.group_by_role != "timestamp" else intent.group_by_role,
        "group_by_role": intent.group_by_role,
        "aggregation": intent.aggregation,
        "order": intent.order,
    }


def execute_dataset_overview(
    df: pd.DataFrame,
    column_profiles: List[Dict]
) -> Dict[str, Any]:
    """Execute dataset overview intent."""
    return {
        "type": "dataset_summary",
        "rows": len(df),
        "columns": len(df.columns),
    }


def execute_clarification_required(
    intent: ClarificationRequiredIntent
) -> Dict[str, Any]:
    """Handle clarification required intent."""
    return {
        "type": "clarification",
        "message": intent.message,
    }


# === Main Execution Function ===

def execute_intent(
    dataset_id: str,
    intent: Intent
) -> ExecutionResult:
    """
    Execute a validated intent on a dataset.
    
    This function:
    1. Loads the dataset
    2. Maps roles to actual columns
    3. Executes the computation
    4. Returns structured results
    
    NO raw data is sent to AI.
    """
    # Load profile for column metadata and filename
    profile_data = storage.get_json(dataset_id, "profile")
    if not profile_data:
        raise ValueError(f"Profile for dataset {dataset_id} not found")
    
    column_profiles = profile_data.get("columns", [])
    dataset_name = profile_data.get("dataset", {}).get("name", "data.csv")
    
    # Load dataset file (stored with original filename)
    dataset_bytes = storage.get_file(dataset_id, dataset_name)
    if not dataset_bytes:
        raise ValueError(f"Dataset file {dataset_name} not found for dataset {dataset_id}")
    
    # Load DataFrame
    df = get_dataframe_from_bytes(dataset_bytes, dataset_name)
    
    # Execute based on intent type
    total_rows = len(df)
    
    try:
        if isinstance(intent, DatasetOverviewIntent):
            result_data = execute_dataset_overview(df, column_profiles)
        elif isinstance(intent, AggregateIntent):
            result_data = execute_aggregate(df, column_profiles, intent, total_rows)
        elif isinstance(intent, CompareIntent):
            result_data = execute_compare(df, column_profiles, intent, total_rows)
        elif isinstance(intent, RankIntent):
            result_data = execute_rank(df, column_profiles, intent, total_rows)
        elif isinstance(intent, ClarificationRequiredIntent):
            result_data = execute_clarification_required(intent)
        else:
            raise ValueError(f"Unknown intent type: {type(intent)}")
        
        # Post-execution validation
        _validate_result(result_data, total_rows)
        
        return ExecutionResult(
            dataset_id=dataset_id,
            intent_type=intent.type,
            data=result_data,
            metadata={
                "executed_at": datetime.utcnow().isoformat(),
                "rows_processed": total_rows,
            },
        )
        
    except Exception as e:
        raise ValueError(f"Execution failed: {str(e)}")


def _validate_result(result_data: Dict[str, Any], total_rows: int) -> None:
    """Validate execution results for sanity."""
    result_type = result_data.get("type")
    
    if result_type == "scalar":
        value = result_data.get("value")
        if value is not None:
            # Check for NaN or infinite values
            if isinstance(value, (int, float)):
                if not np.isfinite(value):
                    raise ValueError("Result contains invalid numeric value (NaN or infinite)")
            
            # For count aggregations, value should not exceed total rows
            if "count" in str(result_data.get("aggregation", "")).lower():
                if value > total_rows:
                    raise ValueError(f"Count result ({value}) exceeds total rows ({total_rows})")
    
    elif result_type in ["time_series", "breakdown", "ranking"]:
        data = result_data.get("data", [])
        if not isinstance(data, list):
            raise ValueError(f"Expected list data for {result_type}, got {type(data)}")
        
        # Validate each item
        for item in data:
            if "value" in item:
                value = item["value"]
                if isinstance(value, (int, float)):
                    if not np.isfinite(value):
                        raise ValueError("Result contains invalid numeric value (NaN or infinite)")
                # Count validation
                if "count" in str(result_data.get("aggregation", "")).lower():
                    if value > total_rows:
                        raise ValueError(f"Count value ({value}) exceeds total rows ({total_rows})")
        
        # Ranking limit validation
        if result_type == "ranking" and result_data.get("limit"):
            limit = result_data.get("limit")
            if len(data) > limit:
                raise ValueError(f"Ranking result has {len(data)} items but limit is {limit}")
    
    elif result_type == "dataset_summary":
        rows = result_data.get("rows", 0)
        if rows != total_rows:
            raise ValueError(f"Dataset summary rows ({rows}) doesn't match actual rows ({total_rows})")
    
    elif result_type == "clarification":
        # No validation needed for clarification
        pass
    
    else:
        raise ValueError(f"Unknown result type: {result_type}")

