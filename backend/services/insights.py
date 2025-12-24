"""Structural, rename-invariant insight generation.

This module implements a minimal set of KEY INSIGHTS that are:
- Deterministic
- Rename-invariant
- Based ONLY on structural properties of the data

ALLOWED INSIGHT TYPES (Phase 2):
1) Dataset overview
2) Time coverage (if any timestamp columns exist)
3) Dominant dimension (if any dimension has a value > 40% of rows)
4) Metric range (if any metric spans a wide range)
5) Health context (if any health issues exist)

CRITICAL CONSTRAINTS:
- Column NAMES and VALUE LABELS are NEVER mentioned in text.
- No business semantics, no trends, no recommendations.
"""

from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

from models.schemas import Insight, InsightResult
from services.health_check import classify_column_role


def _create_insight(insight_id: str, title: str, description: str) -> Insight:
    """Helper to create a deterministic Insight object.

    All insights use insight_type="summary" and confidence=1.0 because
    they are purely deterministic structural statements.
    """
    return Insight(
        id=insight_id,
        insight_type="summary",
        title=title,
        description=description,
        confidence=1.0,
        data=None,
    )


def generate_insights(
    dataset_id: str,
    df: pd.DataFrame,
    profile: Dict,
    health: Optional[Dict],
) -> InsightResult:
    """Generate structural key insights for a dataset.

    This function is STRICTLY rename-invariant:
    - It never uses column names or category labels in texts.
    - It only uses structural properties: row counts, column counts,
      data types, uniqueness, value distributions.
    """
    insights: List[Insight] = []

    dataset_info = profile.get("dataset", {})
    columns = profile.get("columns", [])
    total_rows = int(dataset_info.get("rows", len(df)))
    total_columns = int(dataset_info.get("columns", len(df.columns)))

    # ------------------------------------------------------------------
    # 1) Dataset Overview (always)
    # ------------------------------------------------------------------
    overview_title = "Dataset overview"
    overview_desc = (
        f"This dataset contains {total_rows:,} rows and {total_columns} columns."
    )
    insights.append(
        _create_insight(
            insight_id="dataset_overview",
            title=overview_title,
            description=overview_desc,
        )
    )

    # ------------------------------------------------------------------
    # 2) Time Coverage Insight (if any timestamp columns)
    # ------------------------------------------------------------------
    timestamp_cols = [
        col["name"] for col in columns if col.get("dtype") == "datetime"
    ]
    if timestamp_cols and not df.empty:
        # Combine coverage across all timestamp columns
        all_dates: List[datetime] = []
        for col_name in timestamp_cols:
            # Use structural behavior only; renaming columns doesn't change types.
            series = df[col_name]
            parsed = pd.to_datetime(series, errors="coerce")
            non_null = parsed.dropna()
            if not non_null.empty:
                all_dates.append(non_null.min())
                all_dates.append(non_null.max())

        if all_dates:
            start = min(all_dates)
            end = max(all_dates)
            # Use ISO-like date strings without referencing column names.
            start_str = start.date().isoformat()
            end_str = end.date().isoformat()
            time_title = "Time coverage"
            time_desc = f"The time-based data spans from {start_str} to {end_str}."
            insights.append(
                _create_insight(
                    insight_id="time_coverage",
                    title=time_title,
                    description=time_desc,
                )
            )

    # ------------------------------------------------------------------
    # 3) Dominant Dimension Insight
    #    - Look for any dimension column where a single value represents
    #      more than 40% of all rows.
    # ------------------------------------------------------------------
    dominant_found = False
    if total_rows > 0:
        for col in columns:
            col_name = col["name"]
            dtype = col.get("dtype", "text")
            unique_count = int(col.get("unique_count", 0))

            role = classify_column_role(dtype=dtype, unique_count=unique_count, total_rows=total_rows)
            if role != "dimension":
                continue

            series = df[col_name]
            counts = series.value_counts(dropna=True)
            if counts.empty:
                continue

            top_count = int(counts.iloc[0])
            share = top_count / total_rows
            if share > 0.40:
                dominant_found = True
                break

    if dominant_found:
        dominance_title = "Dominant dimension"
        dominance_desc = (
            "One of the dimensions has a single value that appears in more than "
            "40% of all records."
        )
        insights.append(
            _create_insight(
                insight_id="dominant_dimension",
                title=dominance_title,
                description=dominance_desc,
            )
        )

    # ------------------------------------------------------------------
    # 4) Metric Range Insight
    #    - If any metric column spans a wide numeric range.
    #    - We define a 'wide' range as a ratio of at least 1,000 between
    #      largest and smallest non-zero absolute values.
    # ------------------------------------------------------------------
    wide_metric_found = False
    for col in columns:
        col_name = col["name"]
        dtype = col.get("dtype", "text")
        unique_count = int(col.get("unique_count", 0))

        role = classify_column_role(dtype=dtype, unique_count=unique_count, total_rows=total_rows)
        if role != "metric":
            continue

        # Convert to numeric; ignore coercion failures (NaN)
        numeric = pd.to_numeric(df[col_name], errors="coerce").dropna()
        if numeric.empty:
            continue

        abs_vals = numeric.abs()
        non_zero = abs_vals[abs_vals > 0]
        if non_zero.empty:
            continue

        max_val = float(non_zero.max())
        min_val = float(non_zero.min())
        if min_val <= 0:
            continue

        ratio = max_val / min_val
        if ratio >= 1000.0:
            wide_metric_found = True
            break

    if wide_metric_found:
        metric_title = "Wide numeric range"
        metric_desc = (
            "At least one numeric column contains values that span a very wide "
            "range in magnitude."
        )
        insights.append(
            _create_insight(
                insight_id="metric_range",
                title=metric_title,
                description=metric_desc,
            )
        )

    # ------------------------------------------------------------------
    # 5) Health Context Insight
    #    - Only if health issues exist.
    # ------------------------------------------------------------------
    if health and health.get("issues"):
        health_title = "Data quality context"
        health_desc = (
            "Some of the structural observations may be affected by missing or "
            "invalid values in the data."
        )
        insights.append(
            _create_insight(
                insight_id="health_context",
                title=health_title,
                description=health_desc,
            )
        )

    # Build InsightResult
    result = InsightResult(
        dataset_id=dataset_id,
        insights=insights,
        generated_at=datetime.utcnow(),
    )
    return result


