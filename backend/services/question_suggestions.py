"""Dynamic, dataset-aware EDA question generation.

Rules:
- Column names ARE allowed (EDA only, not health).
- Questions are generated from templates per column and filtered so they
  are executable on the current dataset.
- No business semantics; all phrasing is generic.
"""

from typing import Dict, List, Optional

from models.schemas import (
    DatasetProfile,
    HealthCheckResult,
    SuggestedQuestion,
    SuggestedQuestionsResult,
)
from services.health_check import classify_column_role


# Priority for ranking
PRIORITY_ORDER = {
    "time": 1,
    "category": 2,  # category frequency
    "quality": 3,
    "numeric": 4,
}


def _split_roles(profile: DatasetProfile) -> Dict[str, List[str]]:
    """Partition columns by structural role using existing classification."""
    time_cols: List[str] = []
    category_cols: List[str] = []
    numeric_cols: List[str] = []
    # id columns ignored for EDA

    total_rows = profile.dataset.rows
    for col in profile.columns:
        dtype = col.dtype
        unique_count = col.unique_count
        role = classify_column_role(dtype=dtype, unique_count=unique_count, total_rows=total_rows)
        name = col.name

        if role == "timestamp":
            time_cols.append(name)
        elif role == "dimension":
            category_cols.append(name)
        elif role == "metric":
            numeric_cols.append(name)

    return {
        "time": time_cols,
        "category": category_cols,
        "numeric": numeric_cols,
    }


def _has_health_issues(health: Optional[HealthCheckResult]) -> bool:
    return bool(health and health.issues)


def _time_templates(column: str) -> List[SuggestedQuestion]:
    return [
        SuggestedQuestion(
            id=f"time_records_per_{column}",
            text=f"How many records are added per {column}?",
            column=column,
            type="time",
        ),
        SuggestedQuestion(
            id=f"time_change_{column}",
            text=f"How does the number of records change over {column}?",
            column=column,
            type="time",
        ),
        SuggestedQuestion(
            id=f"time_spikes_{column}",
            text=f"Are there spikes or drops over {column}?",
            column=column,
            type="time",
        ),
    ]


def _category_templates(column: str) -> List[SuggestedQuestion]:
    return [
        SuggestedQuestion(
            id=f"cat_freq_{column}",
            text=f"Which {column} values appear most frequently?",
            column=column,
            type="category",
        ),
        SuggestedQuestion(
            id=f"cat_concentration_{column}",
            text=f"Are records heavily concentrated in a few {column} values?",
            column=column,
            type="category",
        ),
        SuggestedQuestion(
            id=f"cat_counts_{column}",
            text=f"How many records exist per {column}?",
            column=column,
            type="category",
        ),
    ]


def _numeric_templates(column: str, has_time: bool) -> List[SuggestedQuestion]:
    questions = [
        SuggestedQuestion(
            id=f"num_distribution_{column}",
            text=f"What is the distribution of {column}?",
            column=column,
            type="numeric",
        ),
        SuggestedQuestion(
            id=f"num_extremes_{column}",
            text=f"Are there extreme values in {column}?",
            column=column,
            type="numeric",
        ),
    ]
    if has_time:
        questions.append(
            SuggestedQuestion(
                id=f"num_over_time_{column}",
                text=f"How does {column} vary over time?",
                column=column,
                type="numeric",
            )
        )
    return questions


def _quality_templates(column: str, has_missing: bool) -> List[SuggestedQuestion]:
    questions: List[SuggestedQuestion] = []
    if has_missing:
        questions.append(
            SuggestedQuestion(
                id=f"quality_missing_{column}",
                text=f"How many records have missing values in {column}?",
                column=column,
                type="quality",
            )
        )
    # Rare/infrequent values: only meaningful for category columns
    # We include the question; executability is ensured by role filter elsewhere.
    questions.append(
        SuggestedQuestion(
            id=f"quality_rare_{column}",
            text=f"Does {column} contain rare or infrequent values?",
            column=column,
            type="quality",
        )
    )
    return questions


def suggest_questions(
    dataset_profile: DatasetProfile,
    health_result: Optional[HealthCheckResult],
) -> SuggestedQuestionsResult:
    """Generate dataset-aware EDA questions.

    Steps:
    1) Classify columns into roles (time, category, numeric).
    2) Expand templates per column role (no fixed generic questions).
    3) Validate executability (required roles/columns must exist).
    4) Rank by priority: time > category > quality > numeric.
    5) Return all questions in deterministic order (frontend can show top 4 by default).
    """
    roles = _split_roles(dataset_profile)
    time_cols = roles["time"]
    category_cols = roles["category"]
    numeric_cols = roles["numeric"]
    has_time = len(time_cols) > 0
    has_health_issues = _has_health_issues(health_result)

    total_rows = dataset_profile.dataset.rows

    # Build lookup for missing counts per column to drive quality templates
    missing_map: Dict[str, int] = {col.name: col.null_count for col in dataset_profile.columns}

    generated: List[SuggestedQuestion] = []

    # Time-based questions (per time column)
    for col in time_cols:
        generated.extend(_time_templates(col))

    # Category-based questions (per category column)
    for col in category_cols:
        generated.extend(_category_templates(col))

    # Numeric-based questions (per numeric column)
    for col in numeric_cols:
        generated.extend(_numeric_templates(col, has_time=has_time))

    # Data-quality questions (per column, only if health issues exist or missing values)
    if has_health_issues or any(missing_map.values()):
        for col in dataset_profile.columns:
            col_name = col.name
            has_missing = missing_map.get(col_name, 0) > 0
            generated.extend(_quality_templates(col_name, has_missing=has_missing))

    # Validation filter: ensure referenced column exists in profile
    existing_columns = {c.name for c in dataset_profile.columns}
    valid_questions: List[SuggestedQuestion] = []
    for q in generated:
        if q.column not in existing_columns:
            continue
        # Role validation: ensure column matches the required type of the question
        col_profile = next(c for c in dataset_profile.columns if c.name == q.column)
        role = classify_column_role(
            dtype=col_profile.dtype,
            unique_count=col_profile.unique_count,
            total_rows=total_rows,
        )
        if q.type == "time" and role != "timestamp":
            continue
        if q.type == "category" and role != "dimension":
            continue
        if q.type == "numeric" and role != "metric":
            continue
        if q.type == "quality":
            # Quality questions are permissible for any column, provided it exists.
            pass
        valid_questions.append(q)

    # Ranking
    def sort_key(q: SuggestedQuestion):
        return (
            PRIORITY_ORDER.get(q.type, 99),
            q.type,
            q.column,
            q.id,
        )

    sorted_questions = sorted(valid_questions, key=sort_key)

    return SuggestedQuestionsResult(
        dataset_id=dataset_profile.dataset.id,
        questions=sorted_questions,
    )



