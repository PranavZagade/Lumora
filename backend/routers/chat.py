"""
Chat Execution API Router.

Handles:
1. Question → Intent generation (LLM)
2. Intent → Execution (backend)
3. Result → Response

CORE PRINCIPLE: Raw data never leaves the server.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from models.intent import (
    IntentRequest,
    IntentResponse,
    ExecutionResult,
    Intent,
    AggregateIntent,
    CompareIntent,
    RankIntent,
    DatasetOverviewIntent,
    ClarificationRequiredIntent,
)
from services.intent_generation import generate_intent
from services.execute_intent import execute_intent
from services.storage import storage
from services.health_check import classify_column_role


router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/{dataset_id}/execute", response_model=Dict[str, Any])
async def execute_question(dataset_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a natural language question on a dataset.
    
    Flow:
    1. Generate intent from question (LLM)
    2. Execute intent on dataset (backend)
    3. Return result
    
    NO raw data is sent to the LLM.
    """
    question = request.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    
    # Load dataset profile to get metadata
    profile_data = storage.get_json(dataset_id, "profile")
    if not profile_data:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    columns = profile_data.get("columns", [])
    total_rows = profile_data.get("dataset", {}).get("rows", 0)
    
    # Build role metadata (NO column names, NO raw data)
    available_roles = set()
    role_counts: Dict[str, int] = {}
    
    for col in columns:
        dtype = col.get("dtype", "text")
        unique_count = col.get("unique_count", 0)
        role = classify_column_role(dtype, unique_count, total_rows)
        available_roles.add(role)
        role_counts[role] = role_counts.get(role, 0) + 1
    
    # Step 1: Generate intent from question
    try:
        intent_request = IntentRequest(
            question=question,
            available_roles=list(available_roles),
            role_counts=role_counts,
            total_rows=total_rows,
        )
        
        intent_response = generate_intent(intent_request)
        intent_dict = intent_response.intent
        
        # Parse into typed intent for validation
        intent_type = intent_dict.get("type")
        if intent_type == "dataset_overview":
            typed_intent = DatasetOverviewIntent(**intent_dict)
        elif intent_type == "aggregate":
            typed_intent = AggregateIntent(**intent_dict)
        elif intent_type == "compare":
            typed_intent = CompareIntent(**intent_dict)
        elif intent_type == "rank":
            typed_intent = RankIntent(**intent_dict)
        elif intent_type == "clarification_required":
            typed_intent = ClarificationRequiredIntent(**intent_dict)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown intent type: {intent_type}")
        
    except ValueError as e:
        # Intent generation failed - return safe clarification
        return {
            "dataset_id": dataset_id,
            "result": {
                "type": "clarification",
                "message": "I couldn't understand your question. Could you rephrase it or be more specific?",
            },
            "metadata": {"error": str(e)},
        }
    except Exception as e:
        # Unexpected error in intent generation
        return {
            "dataset_id": dataset_id,
            "result": {
                "type": "clarification",
                "message": "I encountered an issue processing your question. Please try rephrasing it.",
            },
            "metadata": {"error": str(e)},
        }
    
    # Step 2: Execute intent
    try:
        execution_result = execute_intent(dataset_id, typed_intent)
        
        # Step 3: Return result
        return {
            "dataset_id": dataset_id,
            "result": execution_result.data,
            "metadata": execution_result.metadata,
        }
        
    except ValueError as e:
        # Execution failed - return safe clarification
        error_msg = str(e)
        # Make error message user-friendly
        if "not found" in error_msg.lower():
            user_msg = "I couldn't find the necessary data to answer this question. Please try a different question."
        elif "required" in error_msg.lower() or "missing" in error_msg.lower():
            user_msg = "This question requires data that isn't available in your dataset. Could you try a different question?"
        else:
            user_msg = "I couldn't safely compute this result. Please try rephrasing your question."
        
        return {
            "dataset_id": dataset_id,
            "result": {
                "type": "clarification",
                "message": user_msg,
            },
            "metadata": {"error": error_msg},
        }
    except Exception as e:
        # Unexpected error in execution
        return {
            "dataset_id": dataset_id,
            "result": {
                "type": "clarification",
                "message": "I encountered an unexpected issue. Please try a different question.",
            },
            "metadata": {"error": str(e)},
        }

