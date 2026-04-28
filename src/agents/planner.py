"""
KEEP v2 — Planner Agent

Decomposes user query into 4-6 non-overlapping, research-grade sub-queries.
Includes a safe feedback loop (max 2 refinement attempts).
Also classifies search_mode: web_only | local_only | hybrid.
"""

import json
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage

from src.utils.llm_router import get_llm

from src.schemas.state import ResearchState
from src.utils.logger import get_logger
from src.utils.config import MAX_REFINEMENT_ATTEMPTS, PIPELINE_VERSION

log = get_logger("PlannerAgent")

PLANNER_SYSTEM_PROMPT = """You are a research query planner for an academic citation engine.

Your job:
1. Decompose the user's research topic into exactly 4-6 precise, non-overlapping sub-queries.
2. Classify the search_mode based on whether the user uploaded private documents.

RULES (strict):
1. Each sub-query must be specific and research-grade.
2. Sub-queries must NOT overlap in scope.
3. Include year ranges when relevant (e.g., "2022-2025").
4. Avoid vague terms like "impact of AI" — be precise.
5. search_mode must be one of:
   - "web_only"  — no documents uploaded, use external search only
   - "local_only" — user explicitly wants to query only their uploaded documents
   - "hybrid" — combine both external web search and uploaded document search
6. Output ONLY valid JSON matching the format below. No explanations.

Output format:
{{
  "sub_queries": ["query1", "query2", ...],
  "search_mode": "web_only" | "local_only" | "hybrid"
}}
"""


def planner_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate sub-queries from the user's research query.
    Classifies search_mode based on uploaded document presence.
    Updates state with sub_queries, search_mode, and logs decisions.
    """
    query = state["query"]
    refinement_loops = state.get("refinement_loops", 0)
    llm_call_count = state.get("llm_call_count", 0)
    explainability_log = state.get("explainability_log", [])
    has_uploaded_docs = bool(state.get("uploaded_docs", []))

    log.info(f"Planning sub-queries for: '{query}' (refinement loop {refinement_loops}, docs_uploaded={has_uploaded_docs})")

    llm = get_llm("planner")

    # If this is a refinement loop, instruct the planner to broaden scope
    user_msg = query
    if refinement_loops > 0:
        user_msg = (
            f"Previous queries returned insufficient results. "
            f"Broaden the scope and try different angles.\n\n"
            f"Original topic: {query}"
        )

    # Add context about uploaded documents
    if has_uploaded_docs:
        doc_names = [d.get("filename", "unknown") for d in state["uploaded_docs"]]
        user_msg += (
            f"\n\nContext: The user has uploaded private documents: {', '.join(doc_names)}. "
            f"Consider using 'hybrid' or 'local_only' search mode if the query relates to these documents."
        )
    else:
        user_msg += "\n\nContext: No private documents uploaded. Use 'web_only' search mode."

    response = llm.invoke([
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])

    llm_call_count += 1

    # Parse the JSON response
    try:
        content = response.content.strip()
        # Handle markdown code blocks if LLM wraps output
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        parsed = json.loads(content)

        # Support both old format (array) and new format (object)
        if isinstance(parsed, list):
            sub_queries = parsed
            search_mode = "hybrid" if has_uploaded_docs else "web_only"
        elif isinstance(parsed, dict):
            sub_queries = parsed.get("sub_queries", [query])
            search_mode = parsed.get("search_mode", "hybrid" if has_uploaded_docs else "web_only")
        else:
            raise ValueError("Expected a JSON array or object")

        if not isinstance(sub_queries, list):
            raise ValueError("sub_queries must be a JSON array")

    except (json.JSONDecodeError, ValueError) as e:
        log.error(f"Failed to parse planner output: {e}. Raw: {response.content[:200]}")
        sub_queries = [query]  # Fallback: use original query
        search_mode = "hybrid" if has_uploaded_docs else "web_only"

    # Validate search_mode
    if search_mode not in ("web_only", "local_only", "hybrid"):
        search_mode = "hybrid" if has_uploaded_docs else "web_only"

    # Enforce 4-6 limit
    sub_queries = sub_queries[:6]

    log.info(f"Generated {len(sub_queries)} sub-queries, search_mode='{search_mode}'")
    for i, sq in enumerate(sub_queries):
        log.debug(f"  Sub-query {i+1}: {sq}")

    explainability_log.append({
        "agent": "PlannerAgent",
        "action": "generated_sub_queries",
        "count": len(sub_queries),
        "search_mode": search_mode,
        "refinement_loop": refinement_loops,
        "pipeline_version": PIPELINE_VERSION,
    })

    return {
        **state,
        "sub_queries": sub_queries,
        "search_mode": search_mode,
        "llm_call_count": llm_call_count,
        "explainability_log": explainability_log,
    }
