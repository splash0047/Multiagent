"""
KEEP v2 — Search Agent

Executes sub-queries in parallel across Tavily, arXiv, and DuckDuckGo.
Per-API timeout isolation: 2 sec each within 4 sec total budget.
"""

import concurrent.futures
from typing import Dict, Any, List

import diskcache

from src.tools.tavily_search import tavily_search
from src.tools.arxiv_search import arxiv_search
from src.tools.ddg_search import ddg_search
from src.schemas.state import Source
from src.utils.logger import get_logger
from src.utils.config import LATENCY_BUDGET, PIPELINE_VERSION

log = get_logger("SearchAgent")

# Persistent disk cache shared across runs
_cache = diskcache.Cache(".cache/keep_v2_search")

# Per-API timeout within the total search budget
_PER_API_TIMEOUT = 2  # seconds


def _search_single_query(query: str) -> List[dict]:
    """Run all 3 search adapters in parallel for a single sub-query."""
    combined = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(tavily_search, query, _cache): "Tavily",
            executor.submit(arxiv_search, query, _cache): "arXiv",
            executor.submit(ddg_search, query, _cache): "DDG",
        }
        try:
            for future in concurrent.futures.as_completed(futures, timeout=LATENCY_BUDGET.get("search", 4)):
                adapter_name = futures[future]
                try:
                    results = future.result(timeout=_PER_API_TIMEOUT)
                    combined.extend(results)
                    log.info(f"{adapter_name} returned {len(results)} results")
                except concurrent.futures.TimeoutError:
                    log.warning(f"{adapter_name} TIMED OUT — dropped from aggregation")
                except Exception as e:
                    log.error(f"{adapter_name} FAILED: {e}")
        except concurrent.futures.TimeoutError:
            log.warning("GLOBAL Search Timeout Reached — partial results returned")

    return combined


def search_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute parallel searches for all sub-queries.
    Outputs a deduplicated list of Source objects.
    """
    sub_queries = state.get("sub_queries", [])
    explainability_log = state.get("explainability_log", [])

    log.info(f"Searching across {len(sub_queries)} sub-queries (parallel, 3 adapters)")

    all_raw: List[dict] = []
    for sq in sub_queries:
        results = _search_single_query(sq)
        all_raw.extend(results)

    # URL-level dedup (exact match) before passing to validator
    seen_urls = set()
    unique_sources = []
    for s in all_raw:
        url = s.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            try:
                source = Source(
                    title=s.get("title", "Untitled"),
                    url=url,
                    source_type=s.get("source_type", "blog"),
                    snippet=s.get("snippet", ""),
                )
                unique_sources.append(source.model_dump())
            except Exception as e:
                log.warning(f"Source schema validation failed: {e}")

    log.info(f"Total unique sources after URL dedup: {len(unique_sources)}")

    explainability_log.append({
        "agent": "SearchAgent",
        "action": "parallel_search_completed",
        "total_raw": len(all_raw),
        "unique_after_dedup": len(unique_sources),
        "pipeline_version": PIPELINE_VERSION,
    })

    return {
        **state,
        "sources": unique_sources,
        "explainability_log": explainability_log,
    }
