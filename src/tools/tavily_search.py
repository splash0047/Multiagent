"""
KEEP v2 — Tavily Search Adapter

Primary web search tool with caching and timeout isolation.
"""

import hashlib
import json
from typing import List, Dict
from tenacity import retry, stop_after_attempt, wait_exponential
from tavily import TavilyClient
import os

from src.utils.logger import get_logger
from src.utils.config import LATENCY_BUDGET

log = get_logger("TavilyTool")


def _cache_key(query: str) -> str:
    return f"tavily_{hashlib.md5(query.encode()).hexdigest()}"


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=0.5, max=2))
def _raw_search(client: TavilyClient, query: str, max_results: int = 5) -> list:
    """Execute Tavily search with retry logic."""
    return client.search(query=query, max_results=max_results, search_depth="advanced")


def tavily_search(query: str, cache=None) -> List[Dict]:
    """
    Search using Tavily API.
    Returns list of dicts: {title, url, source_type, snippet}
    """
    # Check cache first
    key = _cache_key(query)
    if cache and key in cache:
        log.info(f"Cache HIT for query: '{query[:50]}...'")
        return cache[key]

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        log.error("TAVILY_API_KEY not set — skipping Tavily search")
        return []

    try:
        client = TavilyClient(api_key=api_key)
        raw = _raw_search(client, query)
        results = raw.get("results", []) if isinstance(raw, dict) else []

        sources = []
        for r in results:
            sources.append({
                "title": r.get("title", "Untitled"),
                "url": r.get("url", ""),
                "source_type": "blog",  # Default; validator will re-classify
                "snippet": r.get("content", "")[:500],
            })

        log.info(f"Tavily returned {len(sources)} results for: '{query[:50]}...'")

        # Cache results
        if cache is not None:
            cache[key] = sources

        return sources

    except Exception as e:
        log.error(f"Tavily search FAILED: {e}")
        return []
