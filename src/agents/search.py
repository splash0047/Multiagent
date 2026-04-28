"""
KEEP v2 — Search Agent

Executes sub-queries in parallel across Tavily, arXiv, and DuckDuckGo.
Supports hybrid routing: web_only | local_only | hybrid.
Per-API timeout isolation: 2 sec each within 4 sec total budget.
"""

import concurrent.futures
from typing import Dict, Any, List

from src.tools.tavily_search import tavily_search
from src.tools.arxiv_search import arxiv_search
from src.tools.ddg_search import ddg_search
from src.schemas.state import Source
from src.utils.logger import get_logger
from src.utils.vector_db import search_similar
from src.utils.config import LATENCY_BUDGET, PIPELINE_VERSION

log = get_logger("SearchAgent")

# Per-API timeout within the total search budget
_PER_API_TIMEOUT = 2  # seconds


def _search_web(query: str) -> List[dict]:
    """Run all 3 external search adapters in parallel for a single sub-query."""
    combined = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(tavily_search, query): "Tavily",
            executor.submit(arxiv_search, query): "arXiv",
            executor.submit(ddg_search, query): "DDG",
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


def _search_local(query: str) -> List[dict]:
    """Search the local VectorDB (Pinecone) for similar document chunks."""
    combined = []
    memory_matches = search_similar(query, k=5, threshold=0.4)
    if memory_matches:
        log.info(f"Local search found {len(memory_matches)} matches for '{query[:30]}...'")
        for match in memory_matches:
            source_url = match["metadata"].get("source_url", "local://unknown")
            combined.append({
                "title": f"📄 Local: {source_url.split('/')[-1].split('#')[0][:30]}",
                "url": source_url,
                "source_type": "docs",
                "snippet": match["text"]
            })
    return combined


def _search_single_query(query: str, search_mode: str) -> List[dict]:
    """
    Route search based on search_mode:
    - web_only: external APIs only (with memory cache check)
    - local_only: Pinecone VectorDB only
    - hybrid: both
    """
    combined = []

    if search_mode == "local_only":
        combined.extend(_search_local(query))

    elif search_mode == "web_only":
        # Still check VectorDB cache for web-based memory
        memory_matches = search_similar(query, k=3, threshold=0.6)
        if memory_matches:
            log.info(f"Skipping external search for '{query[:30]}...' — found {len(memory_matches)} memory matches.")
            for match in memory_matches:
                combined.append({
                    "title": f"Memory: {query[:20]}",
                    "url": match["metadata"].get("source_url", "memory://internal"),
                    "source_type": "memory",
                    "snippet": match["text"]
                })
            return combined
        combined.extend(_search_web(query))

    elif search_mode == "hybrid":
        # Run both local doc search and external search in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            local_future = executor.submit(_search_local, query)
            web_future = executor.submit(_search_web, query)

            try:
                local_results = local_future.result(timeout=LATENCY_BUDGET.get("search", 4))
                combined.extend(local_results)
            except Exception as e:
                log.error(f"Local search failed: {e}")

            try:
                web_results = web_future.result(timeout=LATENCY_BUDGET.get("search", 4))
                combined.extend(web_results)
            except Exception as e:
                log.error(f"Web search failed: {e}")

    else:
        log.warning(f"Unknown search_mode '{search_mode}' — defaulting to web_only")
        combined.extend(_search_web(query))

    return combined


def search_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute searches for all sub-queries with routing.
    Outputs a deduplicated list of Source objects.
    """
    sub_queries = state.get("sub_queries", [])
    search_mode = state.get("search_mode", "web_only")
    explainability_log = state.get("explainability_log", [])

    log.info(f"Searching across {len(sub_queries)} sub-queries (mode={search_mode})")

    all_raw: List[dict] = []
    for sq in sub_queries:
        results = _search_single_query(sq, search_mode)
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
        "search_mode": search_mode,
        "total_raw": len(all_raw),
        "unique_after_dedup": len(unique_sources),
        "pipeline_version": PIPELINE_VERSION,
    })

    return {
        **state,
        "sources": unique_sources,
        "explainability_log": explainability_log,
    }
