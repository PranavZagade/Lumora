"""
Semantic Resolution Service.

Detects semantic concepts from questions and maps them to dataset columns.
CORE PRINCIPLE: Never guess. Only ask for mappings when REQUIRED.

LOGIC RULES:
1. Structural questions NEVER need semantic mappings
2. Only ask for mappings when concept is REQUIRED to answer
3. Refuse subjective/policy questions
4. Never ask for mappings for structural concepts (year, month, quantity, duration)
"""

import re
from typing import Dict, List, Set, Optional, Tuple, Literal, Any
import logging

logger = logging.getLogger(__name__)


# Structural concepts - can be answered without semantic mapping
# These are detected from data structure, not business meaning
STRUCTURAL_CONCEPTS = {
    "quantity": ["quantity", "count", "number", "how many", "how much"],
    "duration": ["duration", "length", "runtime", "time", "how long"],
    "year": ["year", "years"],
    "month": ["month", "months"],
    "date": ["date", "when", "day"],
    "time": ["time", "timestamp"],
}

# Semantic concepts - require business meaning mapping
SEMANTIC_CONCEPTS = {
    "rating": ["rating", "rate", "score", "stars", "review score"],
    "country": ["country", "nation", "countries"],
    "genre": ["genre", "category", "type", "kind", "style"],
    "revenue": ["revenue", "income", "earnings", "sales", "money"],
    "region": ["region", "area", "location", "place"],
    "title": ["title", "name", "movie", "film", "show"],
    "price": ["price", "cost"],
    "status": ["status", "state", "condition"],
    "customer": ["customer", "user", "client"],
    "product": ["product", "item", "goods"],
}

# Subjective/policy keywords - questions that require human judgment
SUBJECTIVE_KEYWORDS = [
    "suitable", "appropriate", "mature", "safe", "unsafe",
    "good", "bad", "best", "worst", "high quality", "low quality",
    "recommended", "should", "must", "must not", "allowed", "forbidden"
]


def classify_question(question: str) -> Literal["structural", "semantic", "subjective"]:
    """
    Classify a question into structural, semantic, or subjective.
    
    Returns:
        - "structural": Can be answered with COUNT, GROUP BY, MIN/MAX on any column
        - "semantic": Requires business concept mapping
        - "subjective": Requires human judgment, should be refused
    """
    question_lower = question.lower()
    
    # Check for subjective keywords first
    for keyword in SUBJECTIVE_KEYWORDS:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, question_lower):
            logger.info(f"Question classified as subjective: {keyword}")
            return "subjective"
    
    # Check if question is purely structural
    # Structural patterns: count, time trends, min/max on any column
    structural_patterns = [
        r"how many",
        r"number of",
        r"count",
        r"which.*has.*most",
        r"which.*has.*highest.*number",
        r"which.*has.*lowest.*number",
        r"how.*changed.*over.*time",
        r"trend.*over.*time",
        r"\bmin\b.*\bmax\b",
        r"\bmax\b.*\bmin\b",
        r"highest.*lowest",
        r"lowest.*highest",
        r"what is the (minimum|maximum|min|max)",
        r"what is the (average|mean|sum|total|avg)",
        r"minimum value",
        r"maximum value",
        r"min value",
        r"max value",
    ]
    
    is_structural = any(re.search(pattern, question_lower) for pattern in structural_patterns)
    
    # If it's about records/rows/dataset structure, it's structural
    if any(word in question_lower for word in ["record", "row", "dataset", "data"]):
        is_structural = True
    
    # If it asks about "value" in a structural context (min/max/average), it's structural
    if re.search(r"\b(min|max|minimum|maximum|average|mean|sum|total|avg)\s+(value|values)", question_lower):
        is_structural = True
    
    # If question mentions semantic concepts, it might be semantic
    semantic_detected = False
    for concept, keywords in SEMANTIC_CONCEPTS.items():
        for keyword in keywords:
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, question_lower):
                semantic_detected = True
                break
        if semantic_detected:
            break
    
    # If structural patterns exist and no semantic concepts, it's structural
    if is_structural and not semantic_detected:
        logger.info("Question classified as structural")
        return "structural"
    
    # If semantic concepts detected, it's semantic
    if semantic_detected:
        logger.info("Question classified as semantic")
        return "semantic"
    
    # Default to structural (can be answered with basic operations)
    logger.info("Question classified as structural (default)")
    return "structural"


def detect_semantic_concepts(question: str) -> Set[str]:
    """
    Detect ONLY semantic concepts (not structural ones).
    
    Returns a set of semantic concept names (e.g., {"rating", "country"}).
    Structural concepts like "year", "quantity", "duration" are excluded.
    """
    question_lower = question.lower()
    detected = set()
    
    # Only check semantic concepts, not structural ones
    for concept, keywords in SEMANTIC_CONCEPTS.items():
        for keyword in keywords:
            # Use word boundaries to avoid partial matches
            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, question_lower):
                detected.add(concept)
                break
    
    logger.info(f"Detected semantic concepts in question: {detected}")
    return detected


def is_concept_required(question: str, concept: str) -> bool:
    """
    Check if a concept is REQUIRED to answer the question.
    
    Returns True only if the concept is necessary for the answer.
    A concept is required if:
    - Question asks "which [concept]" (grouping/ranking)
    - Question asks "by [concept]" (grouping)
    - Question filters "where [concept]" (filtering)
    - Question aggregates "[concept]" (aggregation target)
    """
    question_lower = question.lower()
    
    concept_keywords = SEMANTIC_CONCEPTS.get(concept, [])
    for keyword in concept_keywords:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, question_lower):
            # Pattern: "which [keyword]" - grouping/ranking
            if re.search(rf"\bwhich\s+{re.escape(keyword)}", question_lower):
                return True
            # Pattern: "by [keyword]" - grouping
            if re.search(rf"\bby\s+{re.escape(keyword)}", question_lower):
                return True
            # Pattern: "[keyword] of" or "[keyword] for" - aggregation target
            if re.search(rf"\b{re.escape(keyword)}\s+(of|for|in)", question_lower):
                return True
            # Pattern: "where [keyword]" or "with [keyword]" - filtering
            if re.search(rf"\b(where|with|having)\s+{re.escape(keyword)}", question_lower):
                return True
            # Pattern: "[keyword] is" or "[keyword] has" - filtering/condition
            if re.search(rf"\b{re.escape(keyword)}\s+(is|has|equals|contains)", question_lower):
                return True
            # Pattern: "average [keyword]", "sum of [keyword]", "total [keyword]", etc. - aggregation
            if re.search(rf"\b(avg|average|sum|total|mean|min|max|median)\s+(of\s+)?{re.escape(keyword)}", question_lower):
                return True
            # Pattern: "what is the [aggregation] [keyword]" - aggregation
            if re.search(rf"\bwhat\s+is\s+the\s+(avg|average|sum|total|mean|min|max)\s+{re.escape(keyword)}", question_lower):
                return True
            # Pattern: "the [keyword]" when followed by aggregation context
            if re.search(rf"\bthe\s+{re.escape(keyword)}\b", question_lower):
                # Check if it's in an aggregation context
                if any(agg in question_lower for agg in ["average", "avg", "sum", "total", "mean", "min", "max"]):
                    return True
    
    return False


def check_mappings(
    concepts: Set[str],
    existing_mappings: Dict[str, str]
) -> Tuple[Set[str], Set[str]]:
    """
    Check which concepts have mappings and which are missing.
    
    Returns:
        (mapped_concepts, missing_concepts)
    """
    mapped = set()
    missing = set()
    
    for concept in concepts:
        if concept in existing_mappings:
            mapped.add(concept)
        else:
            missing.add(concept)
    
    return mapped, missing


def get_mapping_clarification_message(missing_concepts: Set[str]) -> str:
    """
    Generate a user-friendly message asking for column mappings.
    """
    if len(missing_concepts) == 1:
        concept = list(missing_concepts)[0]
        return f"To answer this question, I need to know which column represents '{concept}'. Please select the column from your dataset."
    else:
        concepts_list = ", ".join([f"'{c}'" for c in sorted(missing_concepts)])
        return f"To answer this question, I need to know which columns represent: {concepts_list}. Please select the columns from your dataset."


class SemanticResolutionResult:
    """Result of semantic resolution."""
    def __init__(
        self,
        needs_clarification: bool,
        missing_concepts: Optional[Set[str]] = None,
        message: Optional[str] = None,
        mapped_concepts: Optional[Dict[str, str]] = None
    ):
        self.needs_clarification = needs_clarification
        self.missing_concepts = missing_concepts or set()
        self.message = message
        self.mapped_concepts = mapped_concepts or {}


def resolve_semantic_dependencies(
    question: str,
    existing_mappings: Dict[str, str],
    intent_components: Optional[Any] = None
) -> Tuple[List[str], Set[str]]:
    """
    Resolve semantic dependencies in order.
    
    Returns:
        (ordered_dependencies, missing_dependencies)
    """
    from services.intent_decomposition import decompose_intent
    
    if intent_components is None:
        intent_components = decompose_intent(question)
    
    # Collect all semantic concepts mentioned
    detected_concepts = detect_semantic_concepts(question)
    
    # Order dependencies based on question structure
    # If ordering is required, ordering target comes first
    ordered_dependencies = []
    missing_dependencies = set()
    
    # Check ordering target first if present
    if intent_components.requires_ordering and intent_components.ordering_target:
        ordering_concept = None
        # Check if ordering_target matches a semantic concept
        for concept, keywords in SEMANTIC_CONCEPTS.items():
            for keyword in keywords:
                if keyword == intent_components.ordering_target:
                    ordering_concept = concept
                    break
            if ordering_concept:
                break
        
        if ordering_concept and ordering_concept in detected_concepts:
            if ordering_concept not in existing_mappings:
                missing_dependencies.add(ordering_concept)
            ordered_dependencies.append(ordering_concept)
    
    # Add other required concepts
    for concept in detected_concepts:
        if concept not in ordered_dependencies:
            if is_concept_required(question, concept):
                if concept not in existing_mappings:
                    missing_dependencies.add(concept)
                ordered_dependencies.append(concept)
    
    return ordered_dependencies, missing_dependencies


def resolve_semantics(
    question: str,
    existing_mappings: Dict[str, str],
    column_info: Optional[Dict[str, Any]] = None
) -> SemanticResolutionResult:
    """
    Resolve semantic concepts in a question with dependency ordering.
    
    LOGIC:
    1. Classify question (structural/semantic/subjective)
    2. Decompose intent (ordering, groupings, etc.)
    3. Check ordering validity for categorical columns
    4. Resolve dependencies in order
    5. Structural questions → no mapping needed
    6. Subjective questions → refuse
    7. Semantic questions → check if concepts are required and mapped
    
    Returns:
        - If subjective: needs_clarification=True with refusal message
        - If structural: needs_clarification=False, no mappings
        - If ordering invalid: needs_clarification=True with ordering error
        - If semantic and all required concepts mapped: needs_clarification=False, mapped_concepts populated
        - If semantic and missing required concepts: needs_clarification=True, message with clarification request
    """
    from services.intent_decomposition import decompose_intent, check_ordering_validity
    
    # Step 1: Classify question
    question_type = classify_question(question)
    
    # Step 2: Handle subjective questions
    if question_type == "subjective":
        return SemanticResolutionResult(
            needs_clarification=True,
            missing_concepts=set(),
            message="I cannot answer questions that require subjective judgment or policy decisions. Please ask about specific, measurable data instead."
        )
    
    # Step 3: Decompose intent
    intent_components = decompose_intent(question)
    
    # Step 4: Check ordering validity if ordering is required
    if intent_components.requires_ordering and intent_components.ordering_target:
        # Check if ordering target is a semantic concept
        ordering_concept = None
        for concept, keywords in SEMANTIC_CONCEPTS.items():
            for keyword in keywords:
                if keyword == intent_components.ordering_target:
                    ordering_concept = concept
                    break
            if ordering_concept:
                break
        
        if ordering_concept:
            # Check if we have column info to validate
            if column_info:
                # Get mapped column
                mapped_column = existing_mappings.get(ordering_concept)
                if mapped_column:
                    is_valid, error_msg = check_ordering_validity(
                        ordering_concept,
                        column_info,
                        existing_mappings
                    )
                    if not is_valid:
                        return SemanticResolutionResult(
                            needs_clarification=True,
                            missing_concepts=set(),
                            message=error_msg or "Cannot determine ordering for this column type."
                        )
    
    # Step 5: Handle structural questions
    if question_type == "structural":
        # Structural questions never need semantic mappings
        logger.info("Structural question - no semantic mapping required")
        return SemanticResolutionResult(
            needs_clarification=False,
            mapped_concepts={}
        )
    
    # Step 6: Handle semantic questions - resolve dependencies in order
    ordered_dependencies, missing_dependencies = resolve_semantic_dependencies(
        question,
        existing_mappings,
        intent_components
    )
    
    if missing_dependencies:
        # Need clarification for missing dependencies
        # Ask for the FIRST missing dependency (ordered)
        first_missing = sorted(missing_dependencies)[0] if missing_dependencies else None
        if first_missing:
            message = f"To answer this question, I need to know which column represents '{first_missing}'. Please select the column from your dataset."
            return SemanticResolutionResult(
                needs_clarification=True,
                missing_concepts={first_missing},  # Ask for one at a time
                message=message
            )
    
    # Step 7: All required concepts are mapped
    mapped_dict = {
        concept: existing_mappings[concept]
        for concept in ordered_dependencies
        if concept in existing_mappings
    }
    
    return SemanticResolutionResult(
        needs_clarification=False,
        mapped_concepts=mapped_dict
    )

