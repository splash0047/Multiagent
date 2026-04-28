"""
KEEP v2 — Document Ingestion Agent

Handles the full lifecycle of private document uploads:
1. Parse uploaded files (PDF, DOCX, CSV, TXT)
2. Semantically chunk the content
3. Store chunks in Pinecone VectorDB with document-level metadata
4. Return structured ingestion results for the pipeline

This agent works independently of the main research pipeline —
documents are ingested asynchronously and become available as
"local document" sources for future queries.
"""

import uuid
from typing import Dict, Any, List

from src.tools.document_parser import parse_and_chunk, SUPPORTED_EXTENSIONS
from src.utils.vector_db import store_chunks
from src.utils.logger import get_logger

log = get_logger("IngestionAgent")


def ingest_document(filename: str, file_bytes: bytes) -> Dict[str, Any]:
    """
    Ingest a single document: parse → chunk → store in vector DB.

    Returns a summary dict with ingestion metrics.
    """
    log.info(f"Starting ingestion for '{filename}' ({len(file_bytes)} bytes)")

    try:
        # 1. Parse and chunk the document
        result = parse_and_chunk(filename, file_bytes)
        chunks = result["chunks"]

        if not chunks:
            log.warning(f"No chunks extracted from '{filename}' — skipping storage")
            return {
                "filename": filename,
                "status": "warning",
                "message": "No extractable text found in the document.",
                "num_chunks": 0,
            }

        # 2. Prepare for vector DB storage
        # Use a document-scoped URL to tag all chunks from this file
        doc_id = str(uuid.uuid4())[:8]
        doc_url = f"local://{filename}#{doc_id}"

        store_payload = [{
            "source_url": doc_url,
            "chunks": chunks,
        }]

        # 3. Store in Pinecone
        store_chunks(store_payload)

        log.info(
            f"Ingestion complete for '{filename}': "
            f"{result['num_chunks']} chunks, {result['total_characters']} chars"
        )

        return {
            "filename": filename,
            "status": "success",
            "doc_url": doc_url,
            "total_characters": result["total_characters"],
            "num_chunks": result["num_chunks"],
            "metrics_chunks": sum(1 for c in chunks if c.get("metrics_found")),
        }

    except ValueError as e:
        log.error(f"Ingestion failed for '{filename}': {e}")
        return {
            "filename": filename,
            "status": "error",
            "message": str(e),
            "num_chunks": 0,
        }
    except Exception as e:
        log.error(f"Unexpected ingestion error for '{filename}': {e}")
        return {
            "filename": filename,
            "status": "error",
            "message": f"Internal error: {str(e)}",
            "num_chunks": 0,
        }


def ingest_multiple(files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ingest multiple documents.
    files: list of {"filename": str, "content": bytes}
    Returns a list of ingestion result dicts.
    """
    results = []
    for f in files:
        result = ingest_document(f["filename"], f["content"])
        results.append(result)

    total_chunks = sum(r["num_chunks"] for r in results)
    success_count = sum(1 for r in results if r["status"] == "success")
    log.info(f"Batch ingestion: {success_count}/{len(files)} files, {total_chunks} total chunks")

    return results
