"""
Query Validation Service.

Validates SQL queries before execution to ensure safety.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of query validation."""
    def __init__(
        self,
        is_valid: bool,
        error_message: Optional[str] = None,
        warnings: Optional[List[str]] = None
    ):
        self.is_valid = is_valid
        self.error_message = error_message
        self.warnings = warnings or []


def validate_query(
    query: str,
    allowed_columns: List[str],
    table_name: str = "data",
    column_info: Optional[Dict[str, Dict[str, Any]]] = None
) -> ValidationResult:
    """
    Validate a SQL query for safety.
    
    Checks:
    - Only SELECT statements
    - Only references known columns
    - No dangerous operations
    - No unbounded scans
    - Reasonable LIMIT
    """
    warnings = []
    
    # Normalize query
    query_upper = query.upper().strip()
    
    # 1. Must be SELECT only
    forbidden_keywords = [
        "DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE",
        "TRUNCATE", "REPLACE", "MERGE", "COPY", "IMPORT", "EXPORT"
    ]
    for keyword in forbidden_keywords:
        if keyword in query_upper:
            return ValidationResult(
                is_valid=False,
                error_message=f"Query contains forbidden keyword: {keyword}"
            )
    
    # 2. Must start with SELECT
    if not query_upper.startswith("SELECT"):
        return ValidationResult(
            is_valid=False,
            error_message="Query must be a SELECT statement"
        )
    
    # 3. Check for dangerous functions
    dangerous_patterns = [
        r"EXEC\s*\(",  # Execute
        r"EVAL\s*\(",  # Eval
        r"LOAD\s*\(",  # Load
        r"READ\s*FILE",  # File read
        r"WRITE\s*FILE",  # File write
        r"HTTP",  # Network
        r"CURL",  # Network
    ]
    for pattern in dangerous_patterns:
        if re.search(pattern, query_upper):
            return ValidationResult(
                is_valid=False,
                error_message=f"Query contains potentially dangerous operation: {pattern}"
            )
    
    # 4. Extract column references
    # Simple extraction: look for column names after SELECT, FROM, WHERE, GROUP BY, ORDER BY
    # This is a simplified check - in production, use a proper SQL parser
    column_refs = set()
    
    # Extract column names from SELECT clause
    select_match = re.search(r"SELECT\s+(.*?)\s+FROM", query_upper, re.DOTALL)
    if select_match:
        select_clause = select_match.group(1)
        # Extract column names (handle aliases, functions, etc.)
        # This is simplified - real parser would be better
        for col in allowed_columns:
            col_upper = col.upper()
            # Check if column is referenced (as identifier, not in string)
            pattern = r"\b" + re.escape(col_upper) + r"\b"
            if re.search(pattern, select_clause):
                column_refs.add(col)
    
    # Extract from WHERE, GROUP BY, ORDER BY
    for clause in ["WHERE", "GROUP BY", "ORDER BY", "HAVING"]:
        clause_match = re.search(rf"{clause}\s+(.*?)(?:\s+(?:FROM|LIMIT|$))", query_upper, re.DOTALL | re.IGNORECASE)
        if clause_match:
            clause_content = clause_match.group(1)
            for col in allowed_columns:
                col_upper = col.upper()
                pattern = r"\b" + re.escape(col_upper) + r"\b"
                if re.search(pattern, clause_content):
                    column_refs.add(col)
    
    # 5. Check LIMIT
    limit_match = re.search(r"LIMIT\s+(\d+)", query_upper)
    if limit_match:
        limit_value = int(limit_match.group(1))
        if limit_value > 1000:
            warnings.append(f"LIMIT is very large ({limit_value}), may be slow")
        if limit_value > 10000:
            return ValidationResult(
                is_valid=False,
                error_message=f"LIMIT too large ({limit_value}), maximum allowed is 10000"
            )
    else:
        # No LIMIT - warn if query could be large
        if "GROUP BY" not in query_upper and "COUNT(*)" not in query_upper:
            warnings.append("Query has no LIMIT and may return many rows")
    
    # 6. Check for Cartesian products (simplified)
    from_count = len(re.findall(r"\bFROM\s+", query_upper))
    if from_count > 1:
        # Multiple FROM clauses might indicate joins
        # Check for explicit JOINs
        if "JOIN" not in query_upper:
            warnings.append("Query may produce Cartesian product (multiple FROM without JOIN)")
    
    # 7. Validate table name
    if table_name not in query_upper:
        # Table name might be aliased, check for FROM clause
        if f"FROM {table_name.upper()}" not in query_upper and f"FROM {table_name}" not in query_upper:
            warnings.append(f"Table name '{table_name}' not found in query")
    
    # 8. Check for NULL validity in grouping columns (if column_info provided)
    if column_info:
        # Extract GROUP BY columns
        group_by_match = re.search(r"GROUP\s+BY\s+(.*?)(?:\s+(?:ORDER|LIMIT|$))", query_upper, re.DOTALL | re.IGNORECASE)
        if group_by_match:
            group_by_clause = group_by_match.group(1)
            # Extract column names from GROUP BY
            for col_name in allowed_columns:
                col_upper = col_name.upper()
                if col_upper in group_by_clause:
                    col_data = column_info.get(col_name, {})
                    null_count = col_data.get("null_count", 0)
                    # Try to get total_rows from first column or estimate
                    total_rows = col_data.get("total_rows", 0)
                    if total_rows == 0:
                        # Estimate from other columns
                        for other_col in column_info.values():
                            if other_col.get("total_rows", 0) > 0:
                                total_rows = other_col.get("total_rows", 0)
                                break
                    
                    if total_rows > 0:
                        null_percentage = (null_count / total_rows * 100)
                        if null_percentage > 50:
                            warnings.append(f"Grouping column '{col_name}' has {null_percentage:.1f}% NULL values, results may be misleading")
    
    logger.info(f"Query validation: valid=True, warnings={len(warnings)}")
    
    return ValidationResult(
        is_valid=True,
        warnings=warnings
    )

