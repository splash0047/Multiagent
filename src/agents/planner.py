"""
KEEP v2 — Planner Agent

Decomposes user query into 4-6 non-overlapping, research-grade sub-queries.
Includes a safe feedback loop (max 2 refinement attempts).
"""

import json
from typing import Dict, Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from src.schemas.state import ResearchState
from src.utils.logger import get_logger
from src.utils.config import LLM_MODEL, LLM_TEMPERATURE, MAX_REFINEMENT_ATTEMPTS, PIPELINE_VERSION

log = get_logger("PlannerAgent")

PLANNER_SYSTEM_PROMPT = """You are a research query planner for an academic citation engine.

Your job: decompose the user's research topic into exactly 4-6 precise, non-overlapping sub-queries.

RULES (strict):
1. Each sub-query must be specific and research-grade.
2. Sub-queries must NOT overlap in scope.
3. Include year ranges when relevant (e.g., "2022-2025").
4. Avoid vague terms like "impact of AI" — be precise.
5. Output ONLY a JSON array of strings. No explanations.

Example input: "transformer architectures for NLP"
Example output: ["evolution of self-attention mechanisms in NLP 2017-2025", "comparison of BERT GPT and T5 architectures for text classification", "efficient transformer variants for long document processing", "transformer pre-training techniques and their effect on downstream NLP tasks", "recent advances in mixture-of-experts transformer models 2023-2025"]
"""


def planner_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate sub-queries from the user's research query.
    Updates state with sub_queries and logs decisions.
    """
    query = state["query"]
    refinement_loops = state.get("refinement_loops", 0)
    llm_call_count = state.get("llm_call_count", 0)
    explainability_log = state.get("explainability_log", [])

    log.info(f"Planning sub-queries for: '{query}' (refinement loop {refinement_loops})")

    llm = ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE)

    # If this is a refinement loop, instruct the planner to broaden scope
    user_msg = query
    if refinement_loops > 0:
        user_msg = (
            f"Previous queries returned insufficient results. "
            f"Broaden the scope and try different angles.\n\n"
            f"Original topic: {query}"
        )

    response = llm.invoke([
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ])

    llm_call_count += 1

    # Parse the JSON array from the response
    try:
        content = response.content.strip()
        # Handle markdown code blocks if LLM wraps output
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        sub_queries = json.loads(content)
        if not isinstance(sub_queries, list):
            raise ValueError("Expected a JSON array")
    except (json.JSONDecodeError, ValueError) as e:
        log.error(f"Failed to parse planner output: {e}. Raw: {response.content[:200]}")
        sub_queries = [query]  # Fallback: use original query

    # Enforce 4-6 limit
    sub_queries = sub_queries[:6]

    log.info(f"Generated {len(sub_queries)} sub-queries")
    for i, sq in enumerate(sub_queries):
        log.debug(f"  Sub-query {i+1}: {sq}")

    explainability_log.append({
        "agent": "PlannerAgent",
        "action": "generated_sub_queries",
        "count": len(sub_queries),
        "refinement_loop": refinement_loops,
        "pipeline_version": PIPELINE_VERSION,
    })

    return {
        **state,
        "sub_queries": sub_queries,
        "llm_call_count": llm_call_count,
        "explainability_log": explainability_log,
    }
