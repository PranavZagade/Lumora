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

# Visualization services (additive - post-execution only)
from services.result_metadata import build_result_metadata
from services.visualization_eligibility import check_eligibility
from services.chart_spec import generate_chart_spec
from services.chart_validator import validate_chart_spec

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
    
    # EARLY GUARD: Check for unmapped conceptual columns before any other processing
    # This catches cases where concepts are referenced but not yet mapped
    # Only checks for concepts that are likely required (not just mentioned)
    from services.semantic_resolution import detect_semantic_concepts, is_concept_required
    existing_mappings = get_mappings(dataset_id)
    detected_concepts = detect_semantic_concepts(question)
    
    # Filter to only required concepts (concepts that are actually needed to answer)
    required_unmapped_concepts = {
        concept for concept in detected_concepts
        if concept not in existing_mappings and is_concept_required(question, concept)
    }
    
    if required_unmapped_concepts:
        # Trigger column-mapping UI immediately and stop processing
        first_unmapped = sorted(required_unmapped_concepts)[0]  # Get first unmapped concept
        return {
            "dataset_id": dataset_id,
            "result": {
                "type": "column_mapping_required",
                "concept": first_unmapped,  # Single concept for now (one at a time)
                "message": f"To answer this question, I need to know which column represents '{first_unmapped}'. Please select the column from your dataset.",
                "available_columns": column_names,
            },
            "metadata": {
                "semantic_resolution": "needs_mapping",
                "early_guard": True,  # Flag that this was caught by early guard
            },
        }
    
    # Step 1: Semantic resolution - check if question needs concept mappings
    # (This continues with existing logic for cases that pass the early guard)
    semantic_result = resolve_semantics(question, existing_mappings, column_info)
    
    if semantic_result.needs_clarification:
        # Check if it's a subjective question (no missing concepts) or mapping request
        if semantic_result.missing_concepts:
            # Need user to provide column mappings - return structured type
            first_missing = sorted(semantic_result.missing_concepts)[0]  # Ask for one at a time
            return {
                "dataset_id": dataset_id,
                "result": {
                    "type": "column_mapping_required",
                    "concept": first_missing,  # Single concept (one at a time)
                    "message": semantic_result.message or f"To answer this question, I need to know which column represents '{first_missing}'. Please select the column from your dataset.",
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
        # Get existing mappings from storage (in case they were just saved)
        existing_mappings = get_mappings(dataset_id)
        
        # Merge with semantic resolution mappings (semantic_result.mapped_concepts)
        all_mappings = {**existing_mappings, **semantic_result.mapped_concepts}
        
        logger.info(f"Using semantic mappings: {all_mappings}")
        
        query_request = QueryGenerationRequest(
            question=question,
            columns=columns,
            total_rows=total_rows,
            table_name="data",
            semantic_mappings=all_mappings  # Use all mappings (existing + newly resolved)
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
        error_msg = str(e)
        logger.error(f"Query generation failed: {error_msg}")
        
        # Check if it's a rate limit or API error
        if "rate limit" in error_msg.lower() or "429" in error_msg:
            return {
                "dataset_id": dataset_id,
                "result": {
                    "type": "clarification",
                    "message": "The query service is temporarily unavailable due to rate limits. Please try again in a few minutes.",
                },
                "metadata": {"error": error_msg},
            }
        
        # For other errors, provide a more helpful message
        return {
            "dataset_id": dataset_id,
            "result": {
                "type": "clarification",
                "message": f"I couldn't understand your question. Internal Error: {error_msg}",
            },
            "metadata": {"error": error_msg},
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
        
        # Step 6: Generate visualization (post-execution, strictly additive)
        visualization = None
        try:
            result_metadata = build_result_metadata(execution_result.data)
            eligibility = check_eligibility(execution_result.data, result_metadata)
            
            if eligibility.eligible:
                chart_spec = generate_chart_spec(
                    execution_result.data,
                    result_metadata,
                    eligibility
                )
                if chart_spec:
                    validation = validate_chart_spec(
                        chart_spec.to_dict(),
                        execution_result.data
                    )
                    if validation.valid:
                        visualization = chart_spec.to_dict()
                        logger.info(f"Visualization generated: {chart_spec.chart_type}")
                    else:
                        logger.warning(f"Chart validation failed: {validation.error}")
        except Exception as viz_error:
            logger.warning(f"Visualization generation failed (graceful degradation): {viz_error}")
            # Continue without visualization - text answer still works
        
        # Step 7: Return formatted result with optional visualization
        return {
            "dataset_id": dataset_id,
            "result": {
                **execution_result.data,
                "message": formatted_message,  # AI-formatted natural language message
            },
            "visualization": visualization,  # NEW: Chart spec or None
            "metadata": {
                **execution_result.metadata,
                "execution_time_ms": execution_result.execution_time_ms,
                "rows_returned": execution_result.rows_returned,
                "query_type": "sql",
                "formatted_by": "ai",  # Indicate AI formatting was used
                "visualization_eligible": visualization is not None,
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

