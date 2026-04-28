"""
KEEP v2 — Extractor Agent

Extracts key findings, metrics, and direct quotes from validated sources.
Includes relevance filtering, information density checks, and coverage tracking.
Fallback: clean text -> summary -> discard.
"""

import json
from typing import Dict, Any, List

from langchain_core.messages import SystemMessage, HumanMessage

from src.utils.llm_router import get_llm

from src.utils.logger import get_logger
from src.utils.vector_db import store_chunks
from src.utils.config import (
    MAX_CHUNKS_PER_SOURCE, MAX_TOKENS_PER_CHUNK,
    MAX_LLM_CALLS, PIPELINE_VERSION,
)

log = get_logger("ExtractorAgent")

EXTRACTOR_SYSTEM_PROMPT = """You are a research data extractor. Your job is to extract structured evidence from source content.

For each source provided, extract up to {max_chunks} chunks. Each chunk must contain:
- Concrete facts, metrics, or data points
- Direct quotes where available
- Specific findings or methodological details

RULES (strict):
1. Max {max_chunks} chunks per source
2. Each chunk max {max_tokens} tokens
3. REJECT chunks that are generic, vague, or contain no factual information
4. Include metrics and numbers whenever present
5. Mark each chunk with metrics_found: true/false

Output JSON format:
[
  {{
    "source_url": "...",
    "chunks": [
      {{"chunk_text": "...", "metrics_found": true}},
      ...
    ],
    "total_available_chunks": <int>
  }}
]

Output ONLY valid JSON. No explanations.
"""


def extractor_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured data from validated sources.
    Tracks coverage ratio and applies noise filtering.
    """
    validated = state.get("validated_sources", [])
    llm_call_count = state.get("llm_call_count", 0)
    explainability_log = state.get("explainability_log", [])

    if not validated:
        log.warning("No validated sources to extract from")
        return {**state, "extracted_data": []}

    # Graceful degradation: if near LLM limit, reduce depth
    remaining_calls = MAX_LLM_CALLS - llm_call_count
    if remaining_calls <= 0:
        log.warning("Circuit breaker: MAX_LLM_CALLS reached — returning snippet-based extraction")
        extracted = []
        for v in validated:
            extracted.append({
                "source_url": v["url"],
                "chunks": [{"chunk_text": v.get("snippet", "")[:MAX_TOKENS_PER_CHUNK], "metrics_found": False}],
                "coverage_ratio": 0.1,
            })
        return {**state, "extracted_data": extracted, "llm_call_count": llm_call_count}

    log.info(f"Extracting from {len(validated)} validated sources")

    llm = get_llm("extractor")

    # Build source content for the LLM
    sources_text = json.dumps(
        [{"source_url": v["url"], "title": v["title"], "content": v.get("snippet", "")}
         for v in validated],
        indent=2,
    )

    prompt = EXTRACTOR_SYSTEM_PROMPT.format(
        max_chunks=MAX_CHUNKS_PER_SOURCE,
        max_tokens=MAX_TOKENS_PER_CHUNK,
    )

    try:
        response = llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=f"Extract structured data from these sources:\n{sources_text}"),
        ])
        llm_call_count += 1

        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        raw_extracted = json.loads(content)
    except Exception as e:
        log.error(f"Extraction LLM call FAILED: {e} — falling back to snippet extraction")
        # Fallback: use raw snippets
        raw_extracted = []
        for v in validated:
            raw_extracted.append({
                "source_url": v["url"],
                "chunks": [{"chunk_text": v.get("snippet", ""), "metrics_found": False}],
                "total_available_chunks": 1,
            })

    # Process and compute coverage ratios
    extracted_data: List[dict] = []
    discarded_chunks = 0

    for item in raw_extracted:
        source_url = item.get("source_url", "")
        chunks = item.get("chunks", [])
        total_available = item.get("total_available_chunks", max(len(chunks), 1))

        # Noise filter: remove chunks with no real info
        quality_chunks = []
        for chunk in chunks[:MAX_CHUNKS_PER_SOURCE]:
            text = chunk.get("chunk_text", "").strip()
            if len(text) < 20:
                discarded_chunks += 1
                continue
            quality_chunks.append(chunk)

        if not quality_chunks:
            log.info(f"All chunks discarded for {source_url[:50]} — low information density")
            explainability_log.append({
                "agent": "ExtractorAgent",
                "action": "source_discarded_no_quality_chunks",
                "url": source_url,
            })
            continue

        coverage_ratio = round(len(quality_chunks) / total_available, 2) if total_available > 0 else 0.0

        extracted_data.append({
            "source_url": source_url,
            "chunks": quality_chunks,
            "coverage_ratio": coverage_ratio,
        })

    log.info(f"Extraction complete: {len(extracted_data)} sources, {discarded_chunks} low-density chunks discarded")

    explainability_log.append({
        "agent": "ExtractorAgent",
        "action": "extraction_complete",
        "sources_extracted": len(extracted_data),
        "chunks_discarded": discarded_chunks,
        "pipeline_version": PIPELINE_VERSION,
    })

    if extracted_data:
        store_chunks(extracted_data)

    return {
        **state,
        "extracted_data": extracted_data,
        "llm_call_count": llm_call_count,
        "explainability_log": explainability_log,
    }
