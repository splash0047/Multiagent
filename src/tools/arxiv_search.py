"""
KEEP v2 — arXiv Search Adapter

Academic paper search with caching and timeout isolation.
"""

import hashlib
import arxiv
from typing import List, Dict
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils.logger import get_logger

log = get_logger("ArxivTool")


def _cache_key(query: str) -> str:
    return f"arxiv_{hashlib.md5(query.encode()).hexdigest()}"


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=0.5, max=2))
def _raw_search(query: str, max_results: int = 5) -> list:
    """Execute arXiv search with retry logic."""
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    return list(client.results(search))


def arxiv_search(query: str) -> List[Dict]:
    """
    Search arXiv for academic papers.
    Returns list of dicts: {title, url, source_type, snippet}
    """
    try:
        results = _raw_search(query)

        sources = []
        for r in results:
            sources.append({
                "title": r.title,
                "url": r.entry_id,
                "source_type": "paper",
                "snippet": r.summary[:500] if r.summary else "",
            })

        log.info(f"arXiv returned {len(sources)} results for: '{query[:50]}...'")

        return sources

    except Exception as e:
        log.error(f"arXiv search FAILED: {e}")
        return []
