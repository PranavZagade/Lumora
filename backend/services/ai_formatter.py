"""
AI Response Formatter Service.

Formats computed query results into natural language using LLM.
CORE PRINCIPLE: AI is a formatter, NOT an analyst. It must NEVER compute or infer.

This service runs AFTER query execution, when results are already final and correct.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from groq import Groq
from services.groq_client import call_with_fallback

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

logger = logging.getLogger(__name__)

# Initialize Groq client
client = None
groq_api_key = os.getenv("GROQ_API_KEY")
if groq_api_key:
    try:
        client = Groq(api_key=groq_api_key)
        logger.info("Groq client initialized for AI formatting")
    except Exception as e:
        logger.warning(f"Failed to initialize Groq client: {e}")
else:
    logger.warning("GROQ_API_KEY not set - AI formatting will be disabled")


def format_result_with_ai(
    question: str,
    result: Dict[str, Any]
) -> str:
    """
    Format a computed query result into natural language using AI.
    
    CRITICAL RULES:
    - AI receives ONLY the question and the final result
    - AI must NOT compute anything
    - AI must NOT infer new facts
    - AI must ONLY format the provided result
    
    Args:
        question: The original user question
        result: The computed result (already validated)
    
    Returns:
        Formatted natural language response
    """
    if client is None:
        # Fallback to rule-based formatting if AI is unavailable
        logger.warning("AI formatter unavailable, using fallback")
        return _fallback_format(result)
    
    try:
        # Prepare the result JSON for the AI
        result_json = json.dumps(result, indent=2, default=str)
        
        system_prompt = """You are a response formatter for a data analysis system.

YOUR ROLE: Format computed results into natural language. You are NOT an analyst.

CRITICAL RULES:
1. You receive a question and a COMPUTED result (already correct)
2. You must format the result ONLY - do NOT compute anything
3. You must NOT infer new facts or add explanations beyond the result
4. You must NOT mention SQL, tables, queries, or technical details
5. You must NOT change the meaning of the result

FORMATTING RULES:
- Clean numeric values: round to 1-2 decimals, remove unnecessary precision
- Use aggregation-aware language:
  * COUNT → "records"
  * AVG → "average"
  * MIN → "minimum"
  * MAX → "maximum"
  * SUM → "total"
  * RATIO → "percentage" (multiply 0-1 values by 100 and add %)
- Respect question intent:
  * Comparative questions → answer comparatively
  * Yes/no questions → answer yes/no explicitly
  * Ranking questions → present ranking clearly
- Human tone: clear, concise, 1-2 sentences, no technical jargon

FORBIDDEN:
- Do NOT recompute values
- Do NOT infer missing context
- Do NOT add explanations beyond the result
- Do NOT use phrases like "based on analysis" or "according to the data"
- Do NOT mention SQL, tables, or queries

OUTPUT FORMAT:
Output ONLY the formatted response text. No explanations, no markdown, no code blocks.
Be direct and human-readable."""

        user_prompt = f"""Question: {question}

Computed Result:
{result_json}

Format this result into a clear, human-readable response. Use ONLY the provided result. Do NOT compute or infer anything."""

        response = call_with_fallback(
            client,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,  # Low temperature for consistent formatting
            max_tokens=200,  # Keep responses concise
        )
        
        formatted_text = response.choices[0].message.content.strip()
        
        # Remove any markdown code blocks if present
        if formatted_text.startswith("```"):
            lines = formatted_text.split("\n")
            formatted_text = "\n".join(lines[1:-1]) if len(lines) > 2 else formatted_text
        
        logger.info(f"AI formatted response: {formatted_text[:100]}...")
        return formatted_text
        
    except Exception as e:
        logger.error(f"AI formatting failed: {e}")
        # Fallback to rule-based formatting
        return _fallback_format(result)


def _fallback_format(result: Dict[str, Any]) -> str:
    """
    Fallback rule-based formatting if AI is unavailable.
    This is a simple formatter that doesn't require AI.
    """
    from services.response_formatter import format_result
    
    # Create a minimal query string for the formatter
    query = "SELECT * FROM data"  # Dummy query, not used for formatting
    
    # Use the existing rule-based formatter
    return format_result(result, query, question=None, total_rows=None)

