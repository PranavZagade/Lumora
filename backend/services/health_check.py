"""
Business-aware Data Health Check Service.

CORE PRINCIPLE: Column names must NEVER influence logic.
All decisions are based on DATA BEHAVIOR, not semantics or naming.

Validation: If all column names are randomly renamed, behavior must be identical.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Literal, Optional, Dict, List
from dataclasses import dataclass


# === Type Definitions ===

ColumnRole = Literal["identifier", "timestamp", "metric", "dimension"]
Severity = Literal["low", "medium", "high"]
IssueType = Literal["missing", "duplicate", "format"]
OverallHealth = Literal["good", "fair", "poor"]


# === STATIC TRANSPARENCY PANEL ===
# This list is FIXED and NEVER changes based on what issues are found.
# It exists for user trust and clarity about what was checked.

CHECKS_PERFORMED_TEXT = [
    "Missing values",
    "Duplicate rows",
    "Invalid numeric values",
    "Invalid or future dates",
]


# === Column Role Classification (Purely Structural) ===

def classify_column_role(
    dtype: str,
    unique_count: int,
    total_rows: int
) -> ColumnRole:
    """
    Classify a column into a business role using STRUCTURAL rules only.
    
    NO column names are used. Classification is based on:
    - Data type (numeric, datetime, etc.)
    - Uniqueness ratio (unique values / total rows)
    
    Rules (in order of precedence):
    1. If datetime type → timestamp
    2. If unique ratio ≥ 95% → identifier (too unique to aggregate)
    3. If numeric AND unique ratio < 95% → metric (can be aggregated)
    4. Otherwise → dimension (used for grouping)
    """
    unique_ratio = unique_count / total_rows if total_rows > 0 else 0
    
    # Rule 1: Timestamp detection (structural - based on dtype)
    if dtype == "datetime":
        return "timestamp"
    
    # Rule 2: Identifier detection (structural - based on uniqueness)
    # ≥95% unique means it's an identifier, not suitable for aggregation
    if unique_ratio >= 0.95:
        return "identifier"
    
    # Rule 3: Metric detection (structural - numeric that can be aggregated)
    if dtype == "numeric":
        return "metric"
    
    # Rule 4: Dimension (everything else - used for grouping)
    return "dimension"


# === Severity Thresholds ===

@dataclass
class SeverityThresholds:
    """Threshold percentages for severity levels."""
    low_max: float      # Below this → Low (0 means no Low level)
    medium_max: float   # Below this → Medium, above → High


# Role-based thresholds for MISSING VALUES
MISSING_THRESHOLDS: Dict[ColumnRole, SeverityThresholds] = {
    "metric": SeverityThresholds(low_max=2.0, medium_max=10.0),
    "dimension": SeverityThresholds(low_max=5.0, medium_max=15.0),
    "identifier": SeverityThresholds(low_max=0.0, medium_max=0.0),  # Any missing → High
    "timestamp": SeverityThresholds(low_max=0.0, medium_max=1.0),   # <1% → Medium, else High
}

# Thresholds for DUPLICATE ROWS
# 0% → No issue, <1% → Low, 1-5% → Medium, >5% → High
DUPLICATE_THRESHOLDS = SeverityThresholds(low_max=1.0, medium_max=5.0)

# Thresholds for FORMAT ISSUES
FORMAT_THRESHOLDS = SeverityThresholds(low_max=1.0, medium_max=5.0)


# === Severity Calculation ===

def calculate_severity(
    thresholds: SeverityThresholds,
    percentage: float
) -> Severity:
    """
    Calculate severity based on percentage and thresholds.
    
    Returns "low", "medium", or "high".
    """
    if percentage <= 0:
        return "low"
    elif percentage <= thresholds.low_max:
        return "low"
    elif percentage <= thresholds.medium_max:
        return "medium"
    else:
        return "high"


def calculate_missing_severity(role: ColumnRole, missing_percentage: float) -> Severity:
    """Calculate severity for missing values based on column role."""
    if missing_percentage <= 0:
        return "low"
    
    # Special case: identifiers - any missing is high
    if role == "identifier" and missing_percentage > 0:
        return "high"
    
    return calculate_severity(MISSING_THRESHOLDS[role], missing_percentage)


# === Impact Explanations (Generic, Deterministic - No Column Names) ===

MISSING_EXPLANATIONS: dict[ColumnRole, str] = {
    "metric": "This may affect aggregated calculations such as totals and averages.",
    "dimension": "This may reduce grouping and comparison accuracy.",
    "identifier": "Missing identifiers prevent reliable record tracking.",
    "timestamp": "This may affect trend and time-based analysis.",
}

# Static explanation for duplicate rows
DUPLICATE_EXPLANATION = "Duplicate rows can distort counts and aggregated totals."

# Static explanations for format issues
FORMAT_EXPLANATIONS = {
    "invalid_numeric": "Invalid numeric values may affect aggregated calculations.",
    "negative_metric": "Invalid numeric values may affect aggregated calculations.",
    "future_date": "Invalid or future dates may affect trend and time-based analysis.",
    "invalid_date": "Invalid or future dates may affect trend and time-based analysis.",
}


# === Health Issue Data Structure ===

@dataclass
class HealthIssue:
    """A single data quality issue."""
    column: str
    issue_type: IssueType
    severity: Severity
    count: int
    percentage: float
    description: str
    explanation: str
    role: Optional[ColumnRole]


@dataclass
class HealthCheckResult:
    """Complete health check result."""
    dataset_id: str
    total_rows: int
    total_columns: int
    issues: List[HealthIssue]
    overall_health: OverallHealth
    summary: str
    checks_performed: List[str]


# === Main Health Check Function ===

def run_health_check(
    df: pd.DataFrame,
    dataset_id: str,
    column_profiles: List[Dict]
) -> HealthCheckResult:
    """
    Run comprehensive health check on a DataFrame.
    
    ALL logic is structural - NO column names influence decisions.
    
    Checks performed (STATIC - always the same):
    1. Missing values (role-aware severity)
    2. Duplicate rows (exact matches only)
    3. Invalid numeric values (coercion failures, negatives in metrics)
    4. Invalid or future dates (unparseable datetimes, future dates)
    
    Args:
        df: The DataFrame to check
        dataset_id: ID of the dataset
        column_profiles: List of column profiles with dtype info
    
    Returns:
        HealthCheckResult with all issues found
    """
    issues: List[HealthIssue] = []
    total_rows = len(df)
    total_columns = len(df.columns)
    
    # Build column info map
    column_info = {p["name"]: p for p in column_profiles}
    
    # === Check 1: Missing Values ===
    for col in df.columns:
        col_str = str(col)
        profile = column_info.get(col_str, {})
        dtype = profile.get("dtype", "text")
        unique_count = profile.get("unique_count", df[col].nunique())
        
        # Classify column role (STRUCTURAL - no names used)
        role = classify_column_role(dtype, unique_count, total_rows)
        
        # Count missing values
        missing_count = int(df[col].isna().sum())
        
        if missing_count > 0:
            missing_pct = (missing_count / total_rows) * 100
            severity = calculate_missing_severity(role, missing_pct)
            
            issues.append(HealthIssue(
                column=col_str,
                issue_type="missing",
                severity=severity,
                count=missing_count,
                percentage=round(missing_pct, 2),
                description=f"{missing_count:,} rows ({missing_pct:.1f}%) have missing values",
                explanation=MISSING_EXPLANATIONS[role],
                role=role,
            ))
    
    # === Check 2: Duplicate Rows (Exact matches only) ===
    # Uses full-row equality via DataFrame.duplicated()
    # Severity: 0% → No issue, <1% → Low, 1-5% → Medium, >5% → High
    duplicate_mask = df.duplicated(keep="first")
    duplicate_count = int(duplicate_mask.sum())
    
    if duplicate_count > 0:
        dup_pct = (duplicate_count / total_rows) * 100
        severity = calculate_severity(DUPLICATE_THRESHOLDS, dup_pct)
        
        issues.append(HealthIssue(
            column="(all columns)",
            issue_type="duplicate",
            severity=severity,
            count=duplicate_count,
            percentage=round(dup_pct, 2),
            description=f"{duplicate_count:,} exact duplicate rows ({dup_pct:.1f}%)",
            explanation=DUPLICATE_EXPLANATION,
            role=None,
        ))
    
    # === Check 3: Format Validation (Structural Only) ===
    for col in df.columns:
        col_str = str(col)
        profile = column_info.get(col_str, {})
        dtype = profile.get("dtype", "text")
        unique_count = profile.get("unique_count", df[col].nunique())
        
        # Classify role (STRUCTURAL)
        role = classify_column_role(dtype, unique_count, total_rows)
        
        # === Check 3a: METRIC columns - numeric validation ===
        if role == "metric":
            # Convert to numeric, tracking coercion failures
            original_series = df[col]
            numeric_col = pd.to_numeric(original_series, errors="coerce")
            
            # Count non-null values that became NaN after coercion (coercion failures)
            # These are values that CANNOT be converted to numbers
            original_non_null = original_series.notna()
            coerced_null = numeric_col.isna()
            coercion_failures = int((original_non_null & coerced_null).sum())
            
            if coercion_failures > 0:
                coercion_pct = (coercion_failures / total_rows) * 100
                severity = calculate_severity(FORMAT_THRESHOLDS, coercion_pct)
                
                issues.append(HealthIssue(
                    column=col_str,
                    issue_type="format",
                    severity=severity,
                    count=coercion_failures,
                    percentage=round(coercion_pct, 2),
                    description=f"{coercion_failures:,} rows have non-numeric values",
                    explanation=FORMAT_EXPLANATIONS["invalid_numeric"],
                    role=role,
                ))
            
            # Check for negative values (only in successfully coerced values)
            negative_count = int((numeric_col < 0).sum())
            
            if negative_count > 0:
                neg_pct = (negative_count / total_rows) * 100
                severity = calculate_severity(FORMAT_THRESHOLDS, neg_pct)
                
                issues.append(HealthIssue(
                    column=col_str,
                    issue_type="format",
                    severity=severity,
                    count=negative_count,
                    percentage=round(neg_pct, 2),
                    description=f"{negative_count:,} rows have negative values",
                    explanation=FORMAT_EXPLANATIONS["negative_metric"],
                    role=role,
                ))
        
        # === Check 3b: TIMESTAMP columns - datetime validation ===
        if role == "timestamp":
            try:
                original_series = df[col]
                date_col = pd.to_datetime(original_series, errors="coerce")
                
                # Count unparseable datetime values (coercion failures)
                original_non_null = original_series.notna()
                coerced_null = date_col.isna()
                unparseable_count = int((original_non_null & coerced_null).sum())
                
                if unparseable_count > 0:
                    unparseable_pct = (unparseable_count / total_rows) * 100
                    severity = calculate_severity(FORMAT_THRESHOLDS, unparseable_pct)
                    
                    issues.append(HealthIssue(
                        column=col_str,
                        issue_type="format",
                        severity=severity,
                        count=unparseable_count,
                        percentage=round(unparseable_pct, 2),
                        description=f"{unparseable_count:,} rows have unparseable date values",
                        explanation=FORMAT_EXPLANATIONS["invalid_date"],
                        role=role,
                    ))
                
                # Check for future dates (more than 1 year from now)
                future_threshold = datetime.now() + timedelta(days=365)
                future_count = int((date_col > future_threshold).sum())
                
                if future_count > 0:
                    future_pct = (future_count / total_rows) * 100
                    severity = calculate_severity(FORMAT_THRESHOLDS, future_pct)
                    
                    issues.append(HealthIssue(
                        column=col_str,
                        issue_type="format",
                        severity=severity,
                        count=future_count,
                        percentage=round(future_pct, 2),
                        description=f"{future_count:,} rows have dates more than 1 year in the future",
                        explanation=FORMAT_EXPLANATIONS["future_date"],
                        role=role,
                    ))
            except Exception:
                pass  # Skip if date parsing fails entirely
    
    # === Determine Overall Health ===
    high_count = sum(1 for i in issues if i.severity == "high")
    medium_count = sum(1 for i in issues if i.severity == "medium")
    
    if high_count > 0:
        overall_health: OverallHealth = "poor"
    elif medium_count > 0:
        overall_health = "fair"
    else:
        overall_health = "good"
    
    # === Generate Summary ===
    if len(issues) == 0:
        summary = "We checked for missing values, duplicate rows, and invalid formats — none were found."
    else:
        issue_count = len(issues)
        # Clean, future-proof wording that doesn't list issue types mechanically
        summary = f"Found {issue_count} data quality issue{'s' if issue_count != 1 else ''}."
    
    # IMPORTANT: checks_performed is STATIC and NEVER changes
    # This is for user trust and transparency
    return HealthCheckResult(
        dataset_id=dataset_id,
        total_rows=total_rows,
        total_columns=total_columns,
        issues=issues,
        overall_health=overall_health,
        summary=summary,
        checks_performed=CHECKS_PERFORMED_TEXT,  # Static list, always the same
    )


def health_check_to_dict(result: HealthCheckResult) -> dict:
    """Convert HealthCheckResult to JSON-serializable dict."""
    return {
        "dataset_id": result.dataset_id,
        "total_rows": result.total_rows,
        "total_columns": result.total_columns,
        "issues": [
            {
                "column": i.column,
                "issue_type": i.issue_type,
                "severity": i.severity,
                "count": i.count,
                "percentage": i.percentage,
                "description": i.description,
                "explanation": i.explanation,
                "role": i.role,
            }
            for i in result.issues
        ],
        "overall_health": result.overall_health,
        "summary": result.summary,
        "checks_performed": result.checks_performed,
    }
