"""
KEEP v2 — Vector DB Utility
Manages persistent Pinecone storage with Integrated Inference.
"""

import os
from pinecone import Pinecone, SearchQuery
from src.utils.logger import get_logger
import uuid

log = get_logger("VectorDB")

_INDEX_NAME = "keep-v2-memory"

_pc = None
_index = None

def _get_index():
    global _pc, _index
    if _index is None:
        try:
            api_key = os.getenv("PINECONE_API_KEY")
            if not api_key:
                log.warning("PINECONE_API_KEY not set. VectorDB will be disabled.")
                return None
            
            _pc = Pinecone(api_key=api_key)
            _index = _pc.Index(_INDEX_NAME)
        except Exception as e:
            log.error(f"Failed to initialize Pinecone VectorDB: {e}")
            return None
    return _index

def store_chunks(chunks_data: list):
    """
    Store extracted chunks in VectorDB using Pinecone Integrated Inference.
    chunks_data: list of dicts {"source_url": ..., "chunks": [{"chunk_text": ...}, ...]}
    """
    idx = _get_index()
    if not idx:
        return
        
    records = []
    
    for item in chunks_data:
        url = item.get("source_url", "")
        for chunk in item.get("chunks", []):
            text = chunk.get("chunk_text", "").strip()
            if text:
                record = {
                    "_id": str(uuid.uuid4()),
                    "chunk_text": text,
                    "source_url": url,
                    "metrics_found": chunk.get("metrics_found", False)
                }
                records.append(record)
                
    if records:
        try:
            idx.upsert_records(namespace="default", records=records)
            log.info(f"Stored {len(records)} chunks in Pinecone VectorDB")
        except Exception as e:
            log.error(f"Failed to store chunks in Pinecone VectorDB: {e}")

def search_similar(query: str, k: int = 3, threshold: float = 0.5) -> list:
    """
    Search for similar chunks in VectorDB.
    Returns a list of dicts with text and metadata.
    """
    idx = _get_index()
    if not idx:
        return []
        
    try:
        response = idx.search_records(
            namespace="default",
            query=SearchQuery(
                inputs={"text": query},
                top_k=k
            )
        )
        
        filtered = []
        # Pinecone search_records returns a SearchRecordResponse object with 'result' containing 'hits'
        # Or 'matches' as an attribute
        if hasattr(response, 'result') and hasattr(response.result, 'hits'):
            matches = response.result.hits
        elif hasattr(response, 'matches'):
            matches = response.matches
        elif isinstance(response, dict) and 'matches' in response:
            matches = response['matches']
        elif isinstance(response, dict) and 'result' in response and 'hits' in response['result']:
            matches = response['result']['hits']
        else:
            log.error(f"Unknown response format from Pinecone: {type(response)}")
            matches = []

        for match in matches:
            # Depending on how the SDK structures the match:
            score = match.score if hasattr(match, 'score') else match.get('score', 0)
            if score is None:
                score = 0.0
                
            if score >= threshold:
                record = match.record if hasattr(match, 'record') else match.get('record', {})
                # Extract text and metadata
                # Note: Integrated inference returns the original fields back in 'record'
                text = getattr(record, 'chunk_text', '') if hasattr(record, 'chunk_text') else record.get('chunk_text', '')
                source_url = getattr(record, 'source_url', '') if hasattr(record, 'source_url') else record.get('source_url', '')
                
                filtered.append({
                    "text": text,
                    "metadata": {"source_url": source_url},
                    "score": score
                })
        
        if filtered:
            log.info(f"Found {len(filtered)} high-confidence matches in VectorDB for query: '{query[:50]}'")
        return filtered
    except Exception as e:
        log.error(f"Pinecone VectorDB search failed: {e}")
        return []
