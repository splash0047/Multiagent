"""
KEEP v2 — Validator Agent (Deterministic Core)

Scores sources using a weighted deterministic formula.
Hard rejection rules + source type weighting.
Keeps only sources with final_score >= VALIDATOR_MIN_SCORE.
"""

import json
from typing import Dict, Any, List

from langchain_core.messages import SystemMessage, HumanMessage

from src.utils.llm_router import get_llm

from src.utils.logger import get_logger
from src.utils.config import (
    VALIDATOR_MIN_SCORE,
    SOURCE_WEIGHTS, MAX_LLM_CALLS, PIPELINE_VERSION,
)

log = get_logger("ValidatorAgent")

VALIDATOR_SYSTEM_PROMPT = """You are a research source validator. Your job is to score each source on 3 dimensions.

For EACH source, output a JSON object with:
- "url": the source URL
- "credibility": integer 1-10 (author reputation, publication venue)
- "recency": integer 1-10 (how recent; >5 years old without being foundational = low)
- "technical_depth": integer 1-10 (presence of data, methodology, metrics)
- "reject": boolean (true if source should be hard-rejected)
- "reject_reason": string (only if reject=true; e.g. "no author", "outdated blog", "duplicate")

Hard rejection rules (reject=true immediately):
- No identifiable author or organization
- Outdated (>5 years) AND not a foundational/seminal work
- Low-credibility personal blog with no references
- Content is clearly off-topic

Output ONLY a JSON array of objects. No explanations.
"""


def validator_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score and filter sources using deterministic weighted scoring.
    Applies hard rejection rules and source type weighting.
    """
    sources = state.get("sources", [])
    llm_call_count = state.get("llm_call_count", 0)
    explainability_log = state.get("explainability_log", [])

    if not sources:
        log.warning("No sources to validate")
        return {**state, "validated_sources": [], "no_result_flag": True}

    log.info(f"Validating {len(sources)} sources")

    # Circuit breaker check
    if llm_call_count >= MAX_LLM_CALLS:
        log.warning("Circuit breaker: MAX_LLM_CALLS reached — skipping validation LLM call")
        # Fallback: pass all sources with default scores
        validated = []
        for s in sources[:5]:
            validated.append({
                **s,
                "credibility_score": 5.0,
                "recency_score": 5.0,
                "depth_score": 5.0,
                "final_score": 5.0 * SOURCE_WEIGHTS.get(s.get("source_type", "blog"), 0.6),
            })
        return {**state, "validated_sources": validated, "llm_call_count": llm_call_count}

    llm = get_llm("validator")

    # Format sources for the LLM
    sources_text = json.dumps(
        [{"url": s["url"], "title": s["title"], "source_type": s["source_type"], "snippet": s["snippet"][:300]}
         for s in sources],
        indent=2
    )

    response = llm.invoke([
        SystemMessage(content=VALIDATOR_SYSTEM_PROMPT),
        HumanMessage(content=f"Evaluate these sources:\n{sources_text}"),
    ])
    llm_call_count += 1

    # Parse LLM response
    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        scores = json.loads(content)
    except (json.JSONDecodeError, ValueError) as e:
        log.error(f"Failed to parse validator output: {e}")
        scores = []

    # Build validated sources with weighted scoring
    validated: List[dict] = []
    rejected_count = 0
    score_map = {s.get("url", ""): s for s in scores}

    for source in sources:
        url = source["url"]
        score_data = score_map.get(url, {})

        # Hard rejection
        if score_data.get("reject", False):
            reason = score_data.get("reject_reason", "unknown")
            log.info(f"REJECTED source: {url[:60]} — reason: {reason}")
            explainability_log.append({
                "agent": "ValidatorAgent",
                "action": "source_rejected",
                "url": url,
                "reason": reason,
            })
            rejected_count += 1
            continue

        # Compute weighted score
        cred = float(score_data.get("credibility", 5))
        rec = float(score_data.get("recency", 5))
        depth = float(score_data.get("technical_depth", 5))
        base_score = (cred * 0.4) + (rec * 0.3) + (depth * 0.3)

        source_weight = SOURCE_WEIGHTS.get(source.get("source_type", "blog"), 0.6)
        final_score = round(base_score * source_weight, 2)

        if final_score < VALIDATOR_MIN_SCORE:
            log.info(f"FILTERED source (score {final_score} < {VALIDATOR_MIN_SCORE}): {url[:60]}")
            explainability_log.append({
                "agent": "ValidatorAgent",
                "action": "source_filtered_low_score",
                "url": url,
                "final_score": final_score,
            })
            rejected_count += 1
            continue

        validated.append({
            **source,
            "credibility_score": cred,
            "recency_score": rec,
            "depth_score": depth,
            "final_score": final_score,
        })

    # Sort by score descending, keep top 5
    validated.sort(key=lambda x: x["final_score"], reverse=True)
    validated = validated[:5]

    log.info(f"Validation complete: {len(validated)} kept, {rejected_count} rejected/filtered")

    explainability_log.append({
        "agent": "ValidatorAgent",
        "action": "validation_complete",
        "kept": len(validated),
        "rejected": rejected_count,
        "pipeline_version": PIPELINE_VERSION,
    })

    return {
        **state,
        "validated_sources": validated,
        "llm_call_count": llm_call_count,
        "explainability_log": explainability_log,
        "no_result_flag": len(validated) == 0,
        "low_evidence_flag": 0 < len(validated) < 3,
    }
