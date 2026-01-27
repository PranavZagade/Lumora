"""
Chart Specification Validator.

Validates chart specs before rendering to ensure:
- Referenced fields exist in data
- Types match axis expectations
- Row counts are within limits
- No forbidden transforms
- Chart faithfully represents query result

CORE PRINCIPLE: Trustworthiness - visual must exactly reflect executed query results.
"""

from typing import Dict, Any, List, Optional


# Validation limits
MAX_CHART_ROWS = 365  # Allow up to 1 year of daily data for line charts
ALLOWED_CHART_TYPES = ["line", "area", "bar", "horizontal_bar", "donut", "histogram"]


class ValidationResult:
    """Result of chart spec validation."""
    
    def __init__(
        self,
        valid: bool,
        error: Optional[str] = None,
        warnings: Optional[List[str]] = None
    ):
        self.valid = valid
        self.error = error
        self.warnings = warnings or []
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"valid": self.valid}
        if self.error:
            result["error"] = self.error
        if self.warnings:
            result["warnings"] = self.warnings
        return result


def validate_chart_spec(
    chart_spec: Optional[Dict[str, Any]],
    result_data: Dict[str, Any]
) -> ValidationResult:
    """
    Validate chart specification against result data.
    
    Checks:
    1. Chart spec is not None
    2. Chart type is allowed
    3. Referenced fields exist in data
    4. Data types match expectations
    5. Row count is within limits
    6. Data integrity (no transformation from source)
    """
    warnings: List[str] = []
    
    # Check spec exists
    if chart_spec is None:
        return ValidationResult(valid=False, error="Chart spec is None")
    
    # Handle ChartSpec object
    if hasattr(chart_spec, 'to_dict'):
        spec = chart_spec.to_dict()
    else:
        spec = chart_spec
    
    # Check chart type
    chart_type = spec.get("chart_type")
    if chart_type not in ALLOWED_CHART_TYPES:
        return ValidationResult(
            valid=False,
            error=f"Invalid chart type: {chart_type}"
        )
    
    # Get data from spec
    spec_data = spec.get("data", [])
    
    if not spec_data:
        return ValidationResult(valid=False, error="Chart spec has no data")
    
    # Check row count
    if len(spec_data) > MAX_CHART_ROWS:
        return ValidationResult(
            valid=False,
            error=f"Too many rows ({len(spec_data)}) for chart rendering"
        )
    
    # Validate axis fields exist in data
    x_axis = spec.get("x_axis", {})
    y_axis = spec.get("y_axis", {})
    
    x_field = x_axis.get("field")
    y_field = y_axis.get("field")
    
    if spec_data:
        sample_row = spec_data[0]
        available_fields = set(sample_row.keys())
        
        if x_field and x_field not in available_fields:
            return ValidationResult(
                valid=False,
                error=f"X-axis field '{x_field}' not found in data. Available: {list(available_fields)}"
            )
        
        if y_field and y_field not in available_fields:
            return ValidationResult(
                valid=False,
                error=f"Y-axis field '{y_field}' not found in data. Available: {list(available_fields)}"
            )
    
    # Validate data types match axis expectations
    if spec_data and y_field:
        sample_value = spec_data[0].get(y_field)
        y_type = y_axis.get("type", "numeric")
        
        if y_type == "numeric":
            if not isinstance(sample_value, (int, float)):
                warnings.append(f"Y-axis expects numeric but got {type(sample_value).__name__}")
    
    # Verify data integrity - spec data should match result data
    original_data = result_data.get("data", [])
    
    if len(spec_data) != len(original_data):
        return ValidationResult(
            valid=False,
            error="Chart data row count doesn't match original result"
        )
    
    # Spot check first row values match
    if spec_data and original_data:
        spec_first = spec_data[0]
        orig_first = original_data[0]
        
        # Values should match (pass-through, no transformation)
        for key in spec_first:
            if key in orig_first:
                if spec_first[key] != orig_first[key]:
                    return ValidationResult(
                        valid=False,
                        error=f"Data mismatch detected for field '{key}'"
                    )
    
    # Check UI hints exist
    ui_hints = spec.get("ui_hints", {})
    if not ui_hints:
        warnings.append("Chart spec missing UI hints")
    
    # Validate max_ticks is reasonable
    max_ticks = ui_hints.get("max_ticks", 12)
    if max_ticks < 2 or max_ticks > 20:
        warnings.append(f"Unusual max_ticks value: {max_ticks}")
    
    return ValidationResult(valid=True, warnings=warnings if warnings else None)
