"""
Query Generation Service.

CORE PRINCIPLE: LLM generates SQL queries, NEVER computes results.
LLM sees ONLY schema (column names, types), NEVER raw data.

Input: User question + dataset schema
Output: Validated SQL query (DuckDB compatible)
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from groq import Groq
import logging

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Initialize Groq client
_groq_api_key = os.getenv("GROQ_API_KEY")
if _groq_api_key:
    try:
        client = Groq(api_key=_groq_api_key)
    except Exception as e:
        logging.warning(f"Failed to initialize Groq client: {e}")
        client = None
else:
    client = None

logger = logging.getLogger(__name__)


class QueryGenerationRequest:
    """Request for query generation."""
    def __init__(
        self,
        question: str,
        columns: List[Dict[str, Any]],
        total_rows: int,
        table_name: str = "data",
        semantic_mappings: Optional[Dict[str, str]] = None
    ):
        self.question = question
        self.columns = columns
        self.total_rows = total_rows
        self.table_name = table_name
        self.semantic_mappings = semantic_mappings or {}


class QueryGenerationResponse:
    """Response from query generation."""
    def __init__(
        self,
        query: str,
        query_type: str,  # "sql" or "clarification"
        confidence: float = 0.0,
        message: Optional[str] = None
    ):
        self.query = query
        self.query_type = query_type
        self.confidence = confidence
        self.message = message


def generate_query(request: QueryGenerationRequest) -> QueryGenerationResponse:
    """
    Generate a SQL query from a natural language question.
    
    CRITICAL RULES:
    - Output ONLY SELECT statements
    - No DROP, INSERT, UPDATE, DELETE
    - No subqueries beyond GROUP BY / ORDER BY
    - No LIMIT > 1000 unless explicitly requested
    - No imports, file access, network access
    - Column names come from schema only
    """
    if client is None:
        raise ValueError(
            "Groq client not initialized. "
            "Set GROQ_API_KEY environment variable to enable query generation."
        )
    
    # Build column schema for LLM
    column_schema = []
    for col in request.columns:
        col_name = col.get("name", "")
        col_type = col.get("dtype", "text")
        # Map our types to SQL types
        if col_type == "numeric":
            sql_type = "NUMERIC"
        elif col_type == "datetime":
            sql_type = "TIMESTAMP"
        elif col_type == "boolean":
            sql_type = "BOOLEAN"
        else:
            sql_type = "VARCHAR"
        
        column_schema.append({
            "name": col_name,
            "type": sql_type,
            "nullable": col.get("null_count", 0) > 0
        })
    
    system_prompt = """You are a SQL query generator for a data analysis system.

CRITICAL RULES:
1. You MUST output ONLY valid SQL (DuckDB compatible)
2. You MUST use ONLY the columns provided in the schema
3. You MUST output SELECT statements ONLY
4. You MUST NOT include:
   - DROP, INSERT, UPDATE, DELETE
   - Imports or file operations
   - Network access
   - Loops or arbitrary expressions
   - Subqueries beyond GROUP BY / ORDER BY
5. LIMIT must be <= 1000 unless user explicitly asks for more
6. If the question is ambiguous or cannot be answered with SQL, output: {"type": "clarification", "message": "..."}
7. You MUST use mapped columns when semantic mappings are provided - DO NOT substitute or guess
8. DO NOT use MIN() or MAX() on categorical/text columns unless explicitly ordered
9. If you cannot generate correct SQL, return clarification JSON instead of guessing

OUTPUT FORMAT:
- If you can generate SQL: Output ONLY the SQL query, nothing else
- If clarification needed: Output JSON: {"type": "clarification", "message": "..."}

EXAMPLES:

Question: "How many records are in this dataset?"
SQL: SELECT COUNT(*) as count FROM data;

Question: "Which year has the most records?"
SQL: SELECT EXTRACT(YEAR FROM date_column) as year, COUNT(*) as count FROM data GROUP BY year ORDER BY count DESC LIMIT 1;

Question: "Show top 5 categories by count"
SQL: SELECT category_column, COUNT(*) as count FROM data GROUP BY category_column ORDER BY count DESC LIMIT 5;

Question: "What is the average price?"
SQL: SELECT AVG(price_column) as average_price FROM data;

Remember: Output ONLY SQL or clarification JSON. No explanations, no markdown, no code blocks. If mappings are provided, you MUST use them."""

    # Build semantic mappings context if available
    mappings_context = ""
    if request.semantic_mappings:
        mappings_list = [f"'{concept}' is represented by column '{column}'" 
                        for concept, column in request.semantic_mappings.items()]
        mappings_context = f"\nSemantic mappings (MUST USE THESE):\n" + "\n".join(f"- {m}" for m in mappings_list) + "\n"
        mappings_context += "\nCRITICAL: When the question mentions a mapped concept, you MUST use the mapped column. Do NOT use any other column.\n"
    
    user_prompt = f"""Question: {request.question}

Dataset schema:
- Table name: {request.table_name}
- Total rows: {request.total_rows}
- Columns:
{json.dumps(column_schema, indent=2)}
{mappings_context}
Generate a SQL query to answer this question. Use ONLY the columns listed above.
{mappings_context and "When semantic concepts are mentioned, you MUST use the mapped columns from the semantic mappings above. Do NOT substitute or guess." or ""}
Output ONLY the SQL query (or clarification JSON if needed)."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,  # Low temperature for deterministic output
            max_tokens=500,
        )
        
        content = response.choices[0].message.content.strip()
        
        # Check if it's a clarification request
        if content.startswith("{") and "clarification" in content.lower():
            try:
                clarification = json.loads(content)
                return QueryGenerationResponse(
                    query="",
                    query_type="clarification",
                    confidence=0.5,
                    message=clarification.get("message", "Please clarify your question.")
                )
            except json.JSONDecodeError:
                # Fall through to SQL parsing
                pass
        
        # Extract SQL from markdown code blocks if present
        sql_match = re.search(r"```sql\n(.*?)\n```", content, re.DOTALL)
        if sql_match:
            sql = sql_match.group(1).strip()
        else:
            # Try to find SQL without code blocks
            sql = content.strip()
            # Remove any leading/trailing markdown or explanations
            sql = re.sub(r"^.*?(SELECT)", r"\1", sql, flags=re.IGNORECASE | re.DOTALL)
            sql = sql.split(";")[0].strip()  # Take first statement
        
        # Basic validation: must start with SELECT
        if not sql.upper().startswith("SELECT"):
            return QueryGenerationResponse(
                query="",
                query_type="clarification",
                confidence=0.0,
                message="I couldn't generate a valid query. Please rephrase your question."
            )
        
        # Replace table name placeholder if needed
        sql = sql.replace("FROM data", f"FROM {request.table_name}")
        sql = sql.replace("from data", f"from {request.table_name}")
        
        logger.info(f"Generated SQL query: {sql[:200]}...")
        
        return QueryGenerationResponse(
            query=sql,
            query_type="sql",
            confidence=0.9
        )
        
    except Exception as e:
        logger.error(f"Query generation failed: {e}")
        raise ValueError(f"Query generation failed: {str(e)}")

