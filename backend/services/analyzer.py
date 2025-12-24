"""Data analysis service using DuckDB and Pandas."""

import io
import pandas as pd
from pathlib import Path
from typing import Literal, Optional
from datetime import datetime
import uuid


def generate_id() -> str:
    """Generate a unique session/dataset ID."""
    return str(uuid.uuid4())[:12]


def detect_column_type(series: pd.Series) -> Literal["numeric", "categorical", "datetime", "boolean", "text"]:
    """Detect the semantic type of a column."""
    # Check for boolean first
    if series.dtype == bool:
        return "boolean"
    
    unique_values = series.dropna().unique()
    if len(unique_values) <= 2:
        lower_vals = {str(v).lower() for v in unique_values}
        bool_indicators = {"true", "false", "yes", "no", "1", "0", "y", "n"}
        if lower_vals.issubset(bool_indicators):
            return "boolean"
    
    # Check for datetime
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    
    # Try parsing as datetime
    if series.dtype == object:
        try:
            sample = series.dropna().head(100)
            if len(sample) > 0:
                parsed = pd.to_datetime(sample, errors="coerce")
                if parsed.notna().sum() / len(sample) > 0.8:
                    return "datetime"
        except Exception:
            pass
    
    # Check for numeric
    if pd.api.types.is_numeric_dtype(series):
        return "numeric"
    
    # Try parsing as numeric
    if series.dtype == object:
        try:
            numeric = pd.to_numeric(series.dropna().head(100), errors="coerce")
            if numeric.notna().sum() / len(numeric) > 0.8:
                return "numeric"
        except Exception:
            pass
    
    # Categorical vs Text heuristic
    # If unique values < 50% of total and < 100 unique, it's categorical
    unique_ratio = series.nunique() / len(series) if len(series) > 0 else 0
    if unique_ratio < 0.5 and series.nunique() < 100:
        return "categorical"
    
    return "text"


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean a DataFrame by:
    - Removing completely empty rows/columns
    - Detecting and fixing header issues
    - Handling 'Unnamed' columns
    """
    # Remove completely empty rows and columns
    df = df.dropna(how="all", axis=0)
    df = df.dropna(how="all", axis=1)
    
    if df.empty:
        return df
    
    # Check if first row looks like headers (all strings, no nulls)
    # This handles cases where headers are in data rows
    first_row = df.iloc[0]
    unnamed_cols = [c for c in df.columns if str(c).startswith("Unnamed")]
    
    # If most columns are "Unnamed" and first row has string values, use first row as header
    if len(unnamed_cols) > len(df.columns) / 2:
        if first_row.notna().all() and all(isinstance(v, str) for v in first_row.values):
            df.columns = first_row.values
            df = df.iloc[1:].reset_index(drop=True)
    
    # Clean column names
    df.columns = [str(c).strip() if pd.notna(c) else f"Column_{i}" for i, c in enumerate(df.columns)]
    
    # Remove any remaining completely empty rows
    df = df.dropna(how="all", axis=0).reset_index(drop=True)
    
    return df


def find_best_sheet(excel_file: io.BytesIO) -> tuple[str, pd.DataFrame]:
    """
    Find the sheet with the most data in an Excel file.
    Returns (sheet_name, dataframe).
    """
    excel_file.seek(0)
    xl = pd.ExcelFile(excel_file)
    
    best_sheet = None
    best_df = None
    best_size = 0
    
    for sheet_name in xl.sheet_names:
        try:
            # Read sheet
            df = pd.read_excel(xl, sheet_name=sheet_name, header=None)
            
            # Skip empty sheets
            if df.empty:
                continue
            
            # Calculate "data size" (non-null cells)
            size = df.notna().sum().sum()
            
            if size > best_size:
                best_size = size
                best_sheet = sheet_name
                best_df = df
        except Exception:
            continue
    
    if best_df is None:
        raise ValueError("No valid data found in any sheet")
    
    return best_sheet, best_df


def detect_header_row(df: pd.DataFrame) -> int:
    """
    Detect which row contains the headers.
    Returns the row index (0-based).
    """
    # Look at first 10 rows to find the header
    for i in range(min(10, len(df))):
        row = df.iloc[i]
        
        # Skip rows with too many nulls
        if row.isna().sum() > len(row) / 2:
            continue
        
        # Check if row looks like headers (mostly strings, unique values)
        non_null = row.dropna()
        if len(non_null) == 0:
            continue
        
        # Headers are usually strings
        string_count = sum(1 for v in non_null if isinstance(v, str))
        if string_count >= len(non_null) * 0.7:
            # Check for unique values (headers should be unique)
            if len(non_null.unique()) == len(non_null):
                return i
    
    return 0  # Default to first row


def analyze_dataframe(df: pd.DataFrame, filename: str) -> dict:
    """
    Analyze a DataFrame and return profile information.
    
    Returns a dictionary with:
    - dataset: Basic dataset info
    - columns: List of column profiles
    """
    dataset_id = generate_id()
    
    # Dataset info
    dataset_info = {
        "id": dataset_id,
        "name": filename,
        "rows": len(df),
        "columns": len(df.columns),
        "size_bytes": int(df.memory_usage(deep=True).sum()),
        "uploaded_at": datetime.utcnow().isoformat(),
    }
    
    # Column profiles
    columns = []
    for col in df.columns:
        series = df[col]
        dtype = detect_column_type(series)
        null_count = int(series.isna().sum())
        
        # Get sample values (non-null, unique)
        sample_values = (
            series.dropna()
            .astype(str)
            .unique()[:5]
            .tolist()
        )
        
        columns.append({
            "name": str(col),
            "dtype": dtype,
            "null_count": null_count,
            "null_percentage": round(null_count / len(df) * 100, 2) if len(df) > 0 else 0,
            "unique_count": int(series.nunique()),
            "sample_values": sample_values,
        })
    
    return {
        "dataset": dataset_info,
        "columns": columns,
    }


def load_file_to_dataframe(file_path: Path) -> pd.DataFrame:
    """Load a CSV or Excel file into a DataFrame."""
    suffix = file_path.suffix.lower()
    
    if suffix == ".csv":
        # Try different encodings
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                return clean_dataframe(df)
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode CSV file with supported encodings")
    
    elif suffix in [".xlsx", ".xls"]:
        with open(file_path, "rb") as f:
            content = f.read()
        return get_dataframe_from_bytes(content, file_path.name)
    
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def get_dataframe_from_bytes(content: bytes, filename: str) -> pd.DataFrame:
    """Load a DataFrame from file bytes with smart parsing."""
    suffix = Path(filename).suffix.lower()
    
    if suffix == ".csv":
        # Try different encodings
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(io.BytesIO(content), encoding=encoding)
                return clean_dataframe(df)
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode CSV file with supported encodings")
    
    elif suffix in [".xlsx", ".xls"]:
        buffer = io.BytesIO(content)
        
        # Find the best sheet (one with most data)
        sheet_name, raw_df = find_best_sheet(buffer)
        
        # Detect header row
        header_row = detect_header_row(raw_df)
        
        # Re-read with proper header
        buffer.seek(0)
        df = pd.read_excel(buffer, sheet_name=sheet_name, header=header_row)
        
        # Clean the dataframe
        df = clean_dataframe(df)
        
        return df
    
    else:
        raise ValueError(f"Unsupported file type: {suffix}")
