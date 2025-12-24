"""Insights router.

Exposes deterministic, structural key insights derived from:
- Dataset profile
- Raw data (for distributions and ranges)
- Optional health check result
"""

from fastapi import APIRouter, HTTPException

from services.storage import storage
from services.analyzer import get_dataframe_from_bytes
from services.insights import generate_insights
from models.schemas import InsightResult


router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/{dataset_id}", response_model=InsightResult)
async def get_insights(dataset_id: str) -> InsightResult:
    """Generate deterministic structural insights for a dataset.

    This endpoint is STRICTLY:
    - Read-only
    - Deterministic
    - Rename-invariant (no column-name semantics)
    """
    # Load stored profile (required)
    profile = storage.get_json(dataset_id, "profile")
    if not profile:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Load optional health check result (for health context insight)
    health = storage.get_json(dataset_id, "health_check")

    # Find the raw data file in the session directory
    session_dir = storage._get_session_dir(dataset_id)
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Dataset not found")

    data_file = None
    for f in session_dir.iterdir():
        if f.suffix.lower() in [".csv", ".xlsx", ".xls"]:
            data_file = f
            break

    if not data_file:
        raise HTTPException(status_code=404, detail="Data file not found")

    try:
        with open(data_file, "rb") as f:
            content = f.read()

        df = get_dataframe_from_bytes(content, data_file.name)

        result = generate_insights(
            dataset_id=dataset_id,
            df=df,
            profile=profile,
            health=health,
        )
        return result

    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=500,
            detail=f"Error generating insights: {str(exc)}",
        ) from exc


