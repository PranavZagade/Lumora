"""
LLM-based Intent Generation Service.

CORE PRINCIPLE: AI NEVER sees raw data.
AI only converts natural language → structured intent JSON.

Input: User question + dataset metadata (roles, counts)
Output: Validated intent JSON
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from groq import Groq
from services.groq_client import call_with_fallback

# Load environment variables from .env file
# Look for .env in backend directory (parent of services)
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)
from models.intent import (
    Intent,
    AggregateIntent,
    CompareIntent,
    RankIntent,
    DatasetOverviewIntent,
    ClarificationRequiredIntent,
    ColumnRole,
    IntentRequest,
    IntentResponse,
)


# Initialize Groq client
# API key MUST be loaded from environment variable GROQ_API_KEY
_groq_api_key = os.getenv("GROQ_API_KEY")
if _groq_api_key:
    try:
        client: Optional[Groq] = Groq(api_key=_groq_api_key)
    except Exception as e:
        # Log error for debugging but don't fail module import
        import logging
        logging.warning(f"Failed to initialize Groq client: {e}")
        client = None
else:
    client = None


def generate_intent(request: IntentRequest) -> IntentResponse:
    """
    Generate a structured intent from a natural language question.
    
    The LLM receives ONLY:
    - User question
    - Available column roles
    - Counts per role
    
    The LLM NEVER receives:
    - Column names
    - Raw data
    - Sample values
    - Row data
    """
    if client is None:
        raise ValueError(
            "Groq client not initialized. "
            "Set GROQ_API_KEY environment variable to enable intent generation."
        )
    
    # Build context for LLM (metadata only)
    role_summary = ", ".join([f"{count} {role}(s)" for role, count in request.role_counts.items()])
    
    system_prompt = """You are an intent parser for a data analysis system.

Your ONLY job is to convert natural language questions into structured JSON intents.

CRITICAL RULES:
1. DO NOT answer the question
2. DO NOT compute numbers
3. DO NOT reference column names
4. DO NOT guess business meaning
5. DO NOT generate code

You MUST output ONLY valid JSON matching one of these intent types:

1. DATASET_OVERVIEW: Questions about dataset structure
   Use for: "How many records/rows?", "How many columns?"
   {
     "type": "dataset_overview"
   }

2. AGGREGATE: Aggregate metrics over time or dimensions
   Use for: "What is the total?", "When was X lowest?", "Show trend over time"
   {
     "type": "aggregate",
     "metric_role": "metric" | null,  // null only for "count" aggregation
     "group_by_role": "timestamp" | "dimension" | null,
     "aggregation": "sum" | "mean" | "count" | "min" | "max",
     "post_process": "min" | "max" | null,  // Use for "when was X lowest/highest"
     "time_granularity": "day" | "week" | "month" | "quarter" | "year" | null
   }

3. RANK: Rank by metric value (top/bottom N)
   Use for: "Which category is highest?", "Top 5 categories", "Which year has most records?"
   {
     "type": "rank",
     "metric_role": "metric" | null,  // null ONLY for "count" aggregation
     "group_by_role": "dimension" | "timestamp",  // what to rank
     "aggregation": "sum" | "mean" | "count",  // "count" requires metric_role=null
     "order": "desc" | "asc",  // "desc" for highest/top, "asc" for lowest/bottom
     "limit": number,  // e.g., 5 for "top 5"
     "time_granularity": "day" | "week" | "month" | "quarter" | "year" | null  // only if group_by_role="timestamp"
   }

4. COMPARE: Compare metrics across dimensions
   Use for: "Compare values across categories", "Show breakdown by group"
   {
     "type": "compare",
     "metric_role": "metric",
     "dimension_role": "dimension",
     "aggregation": "sum" | "mean" | "count",
     "limit": number
   }

5. CLARIFICATION_REQUIRED: Cannot determine intent
   Use ONLY when question is ambiguous or unclear
   {
     "type": "clarification_required",
     "message": "Please clarify what you want to analyze."
   }

VALIDATION RULES:
- For "count" aggregation, metric_role MUST be null (for both aggregate and rank)
- For "sum", "mean", "min", "max", metric_role MUST be "metric"
- rank.group_by_role can be "dimension" OR "timestamp"
- time_granularity can only be set when group_by_role is "timestamp"
- "when was X lowest/highest" → aggregate with post_process: "min"/"max" and group_by_role: "timestamp"
- "which category/top N" → rank intent with group_by_role: "dimension", aggregation: "count", metric_role: null
- "which year has most records" → rank intent with group_by_role: "timestamp", aggregation: "count", metric_role: null
- "how many records" → dataset_overview

CLARIFICATION RULES:
If a question could mean multiple things (e.g., "which category contributes most" could mean count OR sum), use clarification_required.

You MUST respond with ONLY valid JSON. No explanations, no markdown, no code blocks. Just the JSON object.

Example responses:
{"type": "dataset_overview"}
{"type": "aggregate", "metric_role": "metric", "group_by_role": "timestamp", "aggregation": "sum", "post_process": "min"}
{"type": "rank", "group_by_role": "dimension", "aggregation": "count", "metric_role": null, "order": "desc", "limit": 5}
{"type": "rank", "group_by_role": "timestamp", "aggregation": "count", "metric_role": null, "order": "desc", "limit": 1, "time_granularity": "year"}

Output ONLY the JSON intent, nothing else."""

    user_prompt = f"""Question: {request.question}

Dataset metadata:
- Total rows: {request.total_rows}
- Available roles: {', '.join(request.available_roles)}
- Role counts: {role_summary}

Generate the intent JSON (ONLY JSON, no other text):"""

    try:
        response = call_with_fallback(
            client,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,  # Low temperature for deterministic output
            max_tokens=500,
        )
        
        # Parse JSON response - handle cases where LLM wraps JSON in markdown or adds text
        content = response.choices[0].message.content.strip()
        
        # Try to extract JSON if wrapped in code blocks
        if "```json" in content:
            # Extract JSON from markdown code block
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end != -1:
                content = content[start:end].strip()
        elif "```" in content:
            # Extract from generic code block
            start = content.find("```") + 3
            end = content.find("```", start)
            if end != -1:
                content = content[start:end].strip()
        
        # Try to find JSON object in the response
        if not content.startswith("{"):
            # Look for first { and last }
            start_idx = content.find("{")
            end_idx = content.rfind("}")
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                content = content[start_idx:end_idx + 1]
        
        # Parse JSON
        try:
            intent_dict = json.loads(content)
        except json.JSONDecodeError:
            # Last resort: try to find and extract JSON more aggressively
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content)
            if json_match:
                content = json_match.group(0)
                intent_dict = json.loads(content)
            else:
                raise ValueError(f"Could not extract valid JSON from LLM response. Response was: {content[:200]}")
        
        # Validate and parse into typed intent
        intent = _parse_intent(intent_dict)
        
        # Calculate confidence (simple heuristic: if all required fields present)
        confidence = 0.9 if _has_required_fields(intent_dict) else 0.5
        
        return IntentResponse(intent=intent_dict, confidence=confidence)
        
    except json.JSONDecodeError as e:
        # Log the raw response for debugging
        raw_content = response.choices[0].message.content if 'response' in locals() else "No response received"
        raise ValueError(
            f"Failed to parse LLM response as JSON: {e}\n"
            f"Raw response (first 500 chars): {raw_content[:500]}"
        )
    except Exception as e:
        raise ValueError(f"Intent generation failed: {str(e)}")


def _parse_intent(intent_dict: Dict[str, Any]) -> Intent:
    """Parse and validate intent dictionary into typed intent."""
    intent_type = intent_dict.get("type")
    
    if intent_type == "dataset_overview":
        return DatasetOverviewIntent(**intent_dict)
    elif intent_type == "aggregate":
        return AggregateIntent(**intent_dict)
    elif intent_type == "compare":
        return CompareIntent(**intent_dict)
    elif intent_type == "rank":
        return RankIntent(**intent_dict)
    elif intent_type == "clarification_required":
        return ClarificationRequiredIntent(**intent_dict)
    else:
        raise ValueError(f"Unknown intent type: {intent_type}")


def _has_required_fields(intent_dict: Dict[str, Any]) -> bool:
    """Check if intent has all required fields."""
    intent_type = intent_dict.get("type")
    
    if intent_type == "dataset_overview":
        return True  # No required fields
    elif intent_type == "aggregate":
        # metric_role required for sum/mean/min/max, optional for count
        agg = intent_dict.get("aggregation", "sum")
        if agg in ["sum", "mean", "min", "max", "median", "std"]:
            return intent_dict.get("metric_role") == "metric"
        return True  # count doesn't require metric_role
    elif intent_type == "compare":
        return intent_dict.get("metric_role") == "metric" and intent_dict.get("dimension_role") == "dimension"
    elif intent_type == "rank":
        # group_by_role always required, metric_role null for count
        group_by = intent_dict.get("group_by_role")
        if group_by not in ["dimension", "timestamp"]:
            return False
        agg = intent_dict.get("aggregation", "count")
        if agg == "count":
            return intent_dict.get("metric_role") is None
        else:
            return intent_dict.get("metric_role") == "metric"
    elif intent_type == "clarification_required":
        return True  # message is optional with default
    else:
        return False

