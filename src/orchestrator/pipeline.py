"""
KEEP v2 — LangGraph Orchestrator

Wires together all agents into the locked pipeline architecture:

  User Query -> Planner -> (Refinement Loop) -> Parallel Search ->
  Validator -> Extractor -> Synthesizer -> Citation Verifier ->
  Confidence Engine -> Final Output
"""

from typing import Dict, Any
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END

from src.agents.planner import planner_agent
from src.agents.search import search_agent
from src.agents.validator import validator_agent
from src.agents.extractor import extractor_agent
from src.agents.synthesizer import synthesizer_agent
from src.agents.verifier import citation_verifier, confidence_engine
from src.utils.logger import get_logger
from src.utils.config import MAX_REFINEMENT_ATTEMPTS, PIPELINE_VERSION

# Load .env at module level
load_dotenv()

log = get_logger("Orchestrator")


# ── Routing Functions ──────────────────────────────────────

def should_refine_queries(state: Dict[str, Any]) -> str:
    """
    After search: if too few sources found AND we haven't exceeded
    max refinement attempts, loop back to planner.
    """
    sources = state.get("sources", [])
    refinement_loops = state.get("refinement_loops", 0)

    if len(sources) < 3 and refinement_loops < MAX_REFINEMENT_ATTEMPTS:
        log.info(
            f"Only {len(sources)} sources found — triggering planner refinement "
            f"(attempt {refinement_loops + 1}/{MAX_REFINEMENT_ATTEMPTS})"
        )
        return "refine"
    return "proceed"


def should_abort(state: Dict[str, Any]) -> str:
    """After validator: if no validated sources, abort pipeline."""
    if state.get("no_result_flag", False):
        log.warning("No validated sources — aborting pipeline")
        return "abort"
    return "continue"


# ── Wrapper Nodes ──────────────────────────────────────────

def increment_refinement(state: Dict[str, Any]) -> Dict[str, Any]:
    """Bump the refinement counter before re-entering planner."""
    return {**state, "refinement_loops": state.get("refinement_loops", 0) + 1}


def abort_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Produce a clean abort output when no sources survive validation."""
    log.warning("Pipeline ABORTED — no reliable sources found")
    return {
        **state,
        "final_report": "❌ Unable to generate grounded response — no reliable sources found after validation.",
        "confidence": 0.0,
        "claims": [],
    }


# ── Graph Construction ─────────────────────────────────────

def build_pipeline() -> StateGraph:
    """
    Build the full LangGraph pipeline matching the locked architecture.
    """
    workflow = StateGraph(dict)

    # Add all nodes
    workflow.add_node("planner", planner_agent)
    workflow.add_node("search", search_agent)
    workflow.add_node("increment_refinement", increment_refinement)
    workflow.add_node("validator", validator_agent)
    workflow.add_node("extractor", extractor_agent)
    workflow.add_node("synthesizer", synthesizer_agent)
    workflow.add_node("verifier", citation_verifier)
    workflow.add_node("confidence", confidence_engine)
    workflow.add_node("abort", abort_node)

    # Set entry point
    workflow.set_entry_point("planner")

    # Planner -> Search
    workflow.add_edge("planner", "search")

    # Search -> Conditional: refine or proceed
    workflow.add_conditional_edges(
        "search",
        should_refine_queries,
        {
            "refine": "increment_refinement",
            "proceed": "validator",
        },
    )

    # Refinement loop back to planner
    workflow.add_edge("increment_refinement", "planner")

    # Validator -> Conditional: abort or continue
    workflow.add_conditional_edges(
        "validator",
        should_abort,
        {
            "abort": "abort",
            "continue": "extractor",
        },
    )

    # Linear flow: Extractor -> Synthesizer -> Verifier -> Confidence -> END
    workflow.add_edge("extractor", "synthesizer")
    workflow.add_edge("synthesizer", "verifier")
    workflow.add_edge("verifier", "confidence")
    workflow.add_edge("confidence", END)
    workflow.add_edge("abort", END)

    return workflow


def run_pipeline(query: str) -> Dict[str, Any]:
    """
    Execute the full KEEP v2 pipeline for a given research query.
    Returns the final state dict containing the report, confidence, claims, and logs.
    """
    log.info(f"=== KEEP v2 Pipeline START ({PIPELINE_VERSION}) ===")
    log.info(f"Query: '{query}'")

    workflow = build_pipeline()
    app = workflow.compile()

    initial_state = {
        "query": query,
        "sub_queries": [],
        "sources": [],
        "validated_sources": [],
        "extracted_data": [],
        "claims": [],
        "final_report": "",
        "confidence": 0.0,
        "llm_call_count": 0,
        "refinement_loops": 0,
        "explainability_log": [],
        "low_evidence_flag": False,
        "no_result_flag": False,
    }

    final_state = app.invoke(initial_state)

    log.info(f"=== KEEP v2 Pipeline END — Confidence: {final_state.get('confidence', 0.0)} ===")

    return final_state
