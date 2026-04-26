"""
KEEP v2 — DuckDuckGo Fallback Search Adapter

Lightweight fallback when Tavily or arXiv fail or return too few results.
Uses the free duckduckgo_search library.
"""

import hashlib
from typing import List, Dict
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils.logger import get_logger

log = get_logger("DDGTool")


def _cache_key(query: str) -> str:
    return f"ddg_{hashlib.md5(query.encode()).hexdigest()}"


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=0.5, max=2))
def _raw_search(query: str, max_results: int = 5) -> list:
    """Execute DuckDuckGo search with retry logic."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except ImportError:
        log.warning("duckduckgo_search not installed — DDG fallback unavailable")
        return []


def ddg_search(query: str, cache=None) -> List[Dict]:
    """
    Search DuckDuckGo as a fallback.
    Returns list of dicts: {title, url, source_type, snippet}
    """
    key = _cache_key(query)
    if cache and key in cache:
        log.info(f"Cache HIT for query: '{query[:50]}...'")
        return cache[key]

    try:
        results = _raw_search(query)

        sources = []
        for r in results:
            sources.append({
                "title": r.get("title", "Untitled"),
                "url": r.get("href", r.get("link", "")),
                "source_type": "blog",  # Default; validator re-classifies
                "snippet": r.get("body", r.get("snippet", ""))[:500],
            })

        log.info(f"DDG returned {len(sources)} results for: '{query[:50]}...'")

        if cache is not None:
            cache[key] = sources

        return sources

    except Exception as e:
        log.error(f"DDG search FAILED: {e}")
        return []
