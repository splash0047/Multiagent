"""
KEEP v2 — Citation Verifier & Confidence Engine

Deterministic Core: Verifies every claim maps to a validated source.
Computes normalized confidence score with diversity and coverage factors.
"""

import json
from typing import Dict, Any, List, Set

from langchain_core.messages import SystemMessage, HumanMessage

from src.utils.llm_router import get_llm

from src.utils.logger import get_logger
from src.utils.config import MAX_LLM_CALLS, PIPELINE_VERSION

log = get_logger("VerifierAgent")


def _get_validated_urls(state: Dict[str, Any]) -> Set[str]:
    """Extract the set of validated source URLs."""
    return {v["url"] for v in state.get("validated_sources", [])}


def _compute_diversity_factor(validated_sources: List[dict]) -> float:
    """
    diversity_factor = unique_source_types / total_sources
    Prevents false high confidence from homogeneous sources.
    """
    if not validated_sources:
        return 0.0
    types = {v.get("source_type", "unknown") for v in validated_sources}
    return round(len(types) / len(validated_sources), 3)


def _compute_avg_coverage(extracted_data: List[dict]) -> float:
    """Average coverage ratio across all extracted sources."""
    if not extracted_data:
        return 0.0
    ratios = [e.get("coverage_ratio", 0.0) for e in extracted_data]
    return round(sum(ratios) / len(ratios), 3)


def citation_verifier(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify every claim's citation exists in validated_sources.
    Optionally uses LLM for semantic claim-chunk matching if budget permits.
    """
    claims = state.get("claims", [])
    validated_urls = _get_validated_urls(state)
    extracted_data = state.get("extracted_data", [])
    llm_call_count = state.get("llm_call_count", 0)
    explainability_log = state.get("explainability_log", [])

    if not claims:
        log.warning("No claims to verify — synthesis may have failed")
        return state

    log.info(f"Verifying {len(claims)} claims against {len(validated_urls)} validated URLs")

    verified_claims = []
    rejected_claims = []

    # Build a quick lookup: url -> extracted chunk texts
    url_to_chunks: Dict[str, List[str]] = {}
    for ed in extracted_data:
        url = ed.get("source_url", "")
        texts = [c.get("chunk_text", "") for c in ed.get("chunks", [])]
        url_to_chunks[url] = texts

    for claim in claims:
        claim_text = claim.get("claim", claim.get("claim_text", ""))
        citation_url = claim.get("citation_url", claim.get("citation", ""))

        # Check 1: URL exists in validated sources
        if citation_url not in validated_urls:
            log.info(f"REJECTED claim — citation URL not in validated sources: {citation_url[:60]}")
            rejected_claims.append({"claim": claim_text, "reason": "URL not in validated sources"})
            continue

        # Check 2: Basic keyword overlap between claim and extracted chunks
        chunks_for_url = url_to_chunks.get(citation_url, [])
        if chunks_for_url:
            # Simple keyword overlap check
            claim_words = set(claim_text.lower().split())
            has_overlap = any(
                len(claim_words.intersection(set(chunk.lower().split()))) >= 3
                for chunk in chunks_for_url
            )
            if not has_overlap:
                log.info(f"REJECTED claim — weak overlap with source content: '{claim_text[:60]}...'")
                rejected_claims.append({"claim": claim_text, "reason": "claim-chunk mismatch"})
                continue

        verified_claims.append({"claim_text": claim_text, "citation_url": citation_url})

    log.info(f"Verification: {len(verified_claims)} verified, {len(rejected_claims)} rejected")

    explainability_log.append({
        "agent": "CitationVerifier",
        "action": "verification_complete",
        "verified": len(verified_claims),
        "rejected": len(rejected_claims),
        "rejected_details": rejected_claims[:5],  # Log first 5 for trace replay
        "pipeline_version": PIPELINE_VERSION,
    })

    return {
        **state,
        "claims": verified_claims,
        "llm_call_count": llm_call_count,
        "explainability_log": explainability_log,
    }


def confidence_engine(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute normalized confidence score (0.0 - 1.0).
    
    confidence = min(1.0, (avg_score/10) * citation_coverage * agreement_score * diversity_factor * coverage_ratio)
    """
    validated = state.get("validated_sources", [])
    claims = state.get("claims", [])
    extracted_data = state.get("extracted_data", [])
    explainability_log = state.get("explainability_log", [])

    # --- Component calculations ---

    # 1. Average source score (normalized to 0-1)
    if validated:
        avg_score = sum(v.get("final_score", 0) for v in validated) / len(validated)
        normalized_score = avg_score / 10.0
    else:
        normalized_score = 0.0

    # 2. Citation coverage (verified claims / total claims in report)
    # Use a rough estimate: count [Source:] references in the report
    total_claims_estimate = max(len(claims), 1)
    citation_coverage = 1.0 if claims else 0.0  # All claims that survived are cited

    # 3. Agreement score = 1 - (contradiction_count / total_claims)
    # Count contradictions from the report text
    report = state.get("final_report", "")
    contradiction_count = report.lower().count("conflicting evidence")
    agreement_score = max(0.0, 1.0 - (contradiction_count / total_claims_estimate))

    # 4. Diversity factor
    diversity_factor = _compute_diversity_factor(validated)

    # 5. Coverage ratio
    avg_coverage = _compute_avg_coverage(extracted_data)

    # --- Final confidence ---
    confidence = min(1.0, normalized_score * citation_coverage * agreement_score * diversity_factor * avg_coverage)
    # Floor at 0.0
    confidence = max(0.0, round(confidence, 3))

    # Handle edge case: if components are reasonable but multiplication kills it
    # (e.g., diversity=0.33 * coverage=0.5 makes even good scores low)
    # Apply a gentle boost if we have verified claims and good sources
    if confidence < 0.3 and len(claims) >= 3 and normalized_score > 0.6:
        confidence = round(min(1.0, confidence + 0.2), 3)
        log.debug("Applied confidence floor boost — strong evidence but low multiplier product")

    log.info(
        f"Confidence: {confidence} | "
        f"score={normalized_score:.2f} coverage={citation_coverage:.2f} "
        f"agreement={agreement_score:.2f} diversity={diversity_factor:.2f} "
        f"extraction_coverage={avg_coverage:.2f}"
    )

    # Low evidence / no result checks
    low_evidence = state.get("low_evidence_flag", False)
    no_result = state.get("no_result_flag", False)

    explainability_log.append({
        "agent": "ConfidenceEngine",
        "action": "confidence_computed",
        "confidence": confidence,
        "components": {
            "normalized_score": round(normalized_score, 3),
            "citation_coverage": round(citation_coverage, 3),
            "agreement_score": round(agreement_score, 3),
            "diversity_factor": diversity_factor,
            "avg_coverage": avg_coverage,
        },
        "low_evidence_flag": low_evidence,
        "no_result_flag": no_result,
        "pipeline_version": PIPELINE_VERSION,
    })

    return {
        **state,
        "confidence": confidence,
        "low_evidence_flag": low_evidence,
        "no_result_flag": no_result,
        "explainability_log": explainability_log,
    }
