"""Suggested questions router (EDA-focused).

Questions are dataset-aware, generated from templates per column role,
and filtered so they are executable on the current dataset.
"""

from fastapi import APIRouter, HTTPException

from models.schemas import DatasetProfile, HealthCheckResult, SuggestedQuestionsResult
from services.storage import storage
from services.question_suggestions import suggest_questions


router = APIRouter(prefix="/api/suggested-questions", tags=["suggested_questions"])


@router.get("/{dataset_id}", response_model=SuggestedQuestionsResult)
async def get_suggested_questions(dataset_id: str) -> SuggestedQuestionsResult:
    """Return suggested, dataset-aware EDA questions for a dataset."""
    profile_data = storage.get_json(dataset_id, "profile")
    if not profile_data:
        raise HTTPException(status_code=404, detail="Dataset not found")
    health_data = storage.get_json(dataset_id, "health_check")

    dataset_profile = DatasetProfile(**profile_data)
    health_result = HealthCheckResult(**health_data) if health_data else None

    return suggest_questions(dataset_profile, health_result)


