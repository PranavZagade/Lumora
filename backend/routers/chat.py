"""
Chat Execution API Router.

NEW ARCHITECTURE:
1. Question → SQL Query generation (LLM)
2. Query validation (safety checks)
3. Safe query execution (DuckDB)
4. Result formatting → Natural language

CORE PRINCIPLE: Raw data never leaves the server.
LLM sees ONLY schema (column names, types), NEVER raw data.
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from services.query_generation import QueryGenerationRequest, generate_query
from services.query_validation import validate_query
from services.query_execution import execute_query
from services.semantic_resolution import resolve_semantics
from services.mapping_storage import get_mappings
from services.storage import storage
from services.response_formatter import (
    is_metadata_question,
    format_metadata_response,
    format_result
)
from services.ai_formatter import format_result_with_ai

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/{dataset_id}/execute", response_model=Dict[str, Any])
async def execute_question(dataset_id: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a natural language question on a dataset.
    
    NEW FLOW:
    1. Generate SQL query from question (LLM sees schema only)
    2. Validate query for safety
    3. Execute query safely (DuckDB with constraints)
    4. Return formatted result
    
    NO raw data is sent to the LLM.
    """
    question = request.get("question")
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    
    # Log the question
    logger.info(f"Processing question for dataset {dataset_id}: {question[:100]}")
    
    # Load dataset profile to get schema
    profile_data = storage.get_json(dataset_id, "profile")
    if not profile_data:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    columns = profile_data.get("columns", [])
    total_rows = profile_data.get("dataset", {}).get("rows", 0)
    
    # FIX 1: Metadata short-circuit - answer metadata questions directly
    if is_metadata_question(question):
        metadata_response = format_metadata_response(question, columns, total_rows)
        return {
            "dataset_id": dataset_id,
            "result": {
                "type": "metadata",
                "message": metadata_response,
            },
            "metadata": {
                "query_type": "metadata",
                "bypassed_sql": True,
            },
        }
    
    # Extract column names for validation
    column_names = [col.get("name", "") for col in columns if col.get("name")]
    
    # Build column info dict for validation
    column_info = {
        col.get("name", ""): {
            "dtype": col.get("dtype", "text"),
            "null_count": col.get("null_count", 0),
            "unique_count": col.get("unique_count", 0),
        }
        for col in columns
        if col.get("name")
    }
    
    # Step 1: Semantic resolution - check if question needs concept mappings
    existing_mappings = get_mappings(dataset_id)
    semantic_result = resolve_semantics(question, existing_mappings, column_info)
    
    if semantic_result.needs_clarification:
        # Check if it's a subjective question (no missing concepts) or mapping request
        if semantic_result.missing_concepts:
            # Need user to provide column mappings
            return {
                "dataset_id": dataset_id,
                "result": {
                    "type": "clarification",
                    "message": semantic_result.message,
                    "requires_mapping": True,
                    "missing_concepts": list(semantic_result.missing_concepts),
                    "available_columns": column_names,
                },
                "metadata": {
                    "semantic_resolution": "needs_mapping",
                },
            }
        else:
            # Subjective question - refuse
            return {
                "dataset_id": dataset_id,
                "result": {
                    "type": "clarification",
                    "message": semantic_result.message or "I cannot answer questions that require subjective judgment.",
                },
                "metadata": {
                    "semantic_resolution": "subjective_refused",
                },
            }
    
    # Step 2: Generate SQL query from question (with semantic mappings)
    try:
        query_request = QueryGenerationRequest(
            question=question,
            columns=columns,
            total_rows=total_rows,
            table_name="data",
            semantic_mappings=semantic_result.mapped_concepts
        )
        
        query_response = generate_query(query_request)
        
        # Log generated query
        logger.info(f"Generated query type: {query_response.query_type}, confidence: {query_response.confidence}")
        
        # Handle clarification request
        if query_response.query_type == "clarification":
            return {
                "dataset_id": dataset_id,
                "result": {
                    "type": "clarification",
                    "message": query_response.message or "Please clarify your question.",
                },
                "metadata": {
                    "query_type": "clarification",
                },
            }
        
        query = query_response.query
        
    except ValueError as e:
        logger.error(f"Query generation failed: {e}")
        return {
            "dataset_id": dataset_id,
            "result": {
                "type": "clarification",
                "message": "I couldn't understand your question. Could you rephrase it or be more specific?",
            },
            "metadata": {"error": str(e)},
        }
    except Exception as e:
        logger.error(f"Unexpected error in query generation: {e}")
        return {
            "dataset_id": dataset_id,
            "result": {
                "type": "clarification",
                "message": "I encountered an issue processing your question. Please try rephrasing it.",
            },
            "metadata": {"error": str(e)},
        }
    
    # Step 3: Validate query
    validation_result = validate_query(query, column_names, table_name="data")
    
    if not validation_result.is_valid:
        logger.warning(f"Query validation failed: {validation_result.error_message}")
        return {
            "dataset_id": dataset_id,
            "result": {
                "type": "clarification",
                "message": "I couldn't generate a safe query for this question. Please try rephrasing it.",
            },
            "metadata": {
                "error": validation_result.error_message,
                "warnings": validation_result.warnings,
            },
        }
    
    # Log validation warnings
    if validation_result.warnings:
        logger.warning(f"Query validation warnings: {validation_result.warnings}")
    
    # Step 4: Execute query safely
    try:
        execution_result = execute_query(
            dataset_id=dataset_id,
            query=query,
            table_name="data",
            timeout_seconds=2,
            max_rows=10000
        )
        
        # Log execution
        logger.info(
            f"Query executed successfully: {execution_result.rows_returned} rows, "
            f"{execution_result.execution_time_ms:.2f}ms"
        )
        
        # Step 5: Format result into natural language using AI
        # AI formatting happens AFTER execution - results are final and correct
        try:
            formatted_message = format_result_with_ai(
                question=question,
                result=execution_result.data
            )
        except Exception as e:
            logger.warning(f"AI formatting failed, using fallback: {e}")
            # Fallback to rule-based formatting
            formatted_message = format_result(
                execution_result.data,
                query,
                question=question,
                total_rows=total_rows
            )
        
        # Step 6: Return formatted result
        return {
            "dataset_id": dataset_id,
            "result": {
                **execution_result.data,
                "message": formatted_message,  # AI-formatted natural language message
            },
            "metadata": {
                **execution_result.metadata,
                "execution_time_ms": execution_result.execution_time_ms,
                "rows_returned": execution_result.rows_returned,
                "query_type": "sql",
                "formatted_by": "ai",  # Indicate AI formatting was used
            },
        }
        
    except ValueError as e:
        logger.error(f"Query execution failed: {e}")
        error_msg = str(e)
        # Make error message user-friendly
        if "not found" in error_msg.lower():
            user_msg = "I couldn't find the necessary data to answer this question. Please try a different question."
        elif "timeout" in error_msg.lower():
            user_msg = "This query took too long to execute. Please try a more specific question."
        elif "syntax" in error_msg.lower() or "invalid" in error_msg.lower():
            user_msg = "I couldn't generate a valid query for this question. Please try rephrasing it."
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
        logger.error(f"Unexpected error in query execution: {e}")
        return {
            "dataset_id": dataset_id,
            "result": {
                "type": "clarification",
                "message": "I encountered an unexpected issue. Please try a different question.",
            },
            "metadata": {"error": str(e)},
        }

