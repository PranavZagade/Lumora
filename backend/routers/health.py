"""Health check router for data quality analysis."""

from fastapi import APIRouter, HTTPException
import pandas as pd

from services.storage import storage
from services.analyzer import get_dataframe_from_bytes
from services.health_check import run_health_check, health_check_to_dict

router = APIRouter(prefix="/api/health-check", tags=["health-check"])


@router.get("/{dataset_id}")
async def get_health_check(dataset_id: str):
    """
    Run a comprehensive health check on a dataset.
    
    Checks performed:
    - Missing values (role-aware severity)
    - Duplicate rows
    - Format validation (negatives, future dates)
    
    Returns business-aware severity levels and impact explanations.
    """
    # Get the stored profile
    profile = storage.get_json(dataset_id, "profile")
    if not profile:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check if health check is already cached
    cached_health = storage.get_json(dataset_id, "health_check")
    if cached_health:
        return cached_health
    
    # Get the raw file to run health check
    # Find the original file in the session
    session_dir = storage._get_session_dir(dataset_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Find the data file (not json files)
    data_file = None
    for f in session_dir.iterdir():
        if f.suffix.lower() in [".csv", ".xlsx", ".xls"]:
            data_file = f
            break
    
    if not data_file:
        raise HTTPException(status_code=404, detail="Data file not found")
    
    try:
        # Load the DataFrame
        with open(data_file, "rb") as f:
            content = f.read()
        df = get_dataframe_from_bytes(content, data_file.name)
        
        # Run health check
        result = run_health_check(
            df=df,
            dataset_id=dataset_id,
            column_profiles=profile.get("columns", [])
        )
        
        # Convert to dict and cache
        result_dict = health_check_to_dict(result)
        storage.save_json(dataset_id, "health_check", result_dict)
        
        return result_dict
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running health check: {str(e)}")


