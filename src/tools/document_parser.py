"""
KEEP v2 — Document Parser Tool

Parses PDF, DOCX, CSV, and TXT files into raw text,
then applies semantic chunking for downstream ingestion.
"""

import csv
import io
import re
from pathlib import Path
from typing import List, Dict

from src.utils.logger import get_logger

log = get_logger("DocumentParser")

# ── Configuration ──────────────────────────────────────────
CHUNK_SIZE = 800       # target characters per chunk
CHUNK_OVERLAP = 100    # overlap between adjacent chunks
MIN_CHUNK_LENGTH = 50  # discard fragments shorter than this


# ── File Parsers ───────────────────────────────────────────

def _parse_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file."""
    from PyPDF2 import PdfReader
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text.strip())
    return "\n\n".join(pages)


def _parse_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file."""
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _parse_csv(file_bytes: bytes) -> str:
    """Convert CSV rows into readable text blocks."""
    text_io = io.StringIO(file_bytes.decode("utf-8", errors="replace"))
    reader = csv.DictReader(text_io)
    rows = []
    for row in reader:
        row_text = " | ".join(f"{k}: {v}" for k, v in row.items() if v)
        if row_text:
            rows.append(row_text)
    return "\n".join(rows)


def _parse_txt(file_bytes: bytes) -> str:
    """Plain text pass-through."""
    return file_bytes.decode("utf-8", errors="replace")


_PARSERS = {
    ".pdf": _parse_pdf,
    ".docx": _parse_docx,
    ".csv": _parse_csv,
    ".txt": _parse_txt,
    ".md": _parse_txt,
}

SUPPORTED_EXTENSIONS = set(_PARSERS.keys())


def parse_file(filename: str, file_bytes: bytes) -> str:
    """
    Parse a file into raw text.
    Raises ValueError for unsupported file types.
    """
    ext = Path(filename).suffix.lower()
    parser = _PARSERS.get(ext)
    if parser is None:
        raise ValueError(
            f"Unsupported file type '{ext}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    log.info(f"Parsing '{filename}' ({ext}, {len(file_bytes)} bytes)")
    raw_text = parser(file_bytes)
    log.info(f"Extracted {len(raw_text)} characters from '{filename}'")
    return raw_text


# ── Semantic Chunking ──────────────────────────────────────

def _split_into_paragraphs(text: str) -> List[str]:
    """Split text on double-newlines or paragraph-like boundaries."""
    # Split on multiple newlines
    blocks = re.split(r'\n{2,}', text)
    # Further split very large blocks on sentence boundaries
    result = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if len(block) <= CHUNK_SIZE:
            result.append(block)
        else:
            # Split on sentence endings
            sentences = re.split(r'(?<=[.!?])\s+', block)
            result.extend(sentences)
    return result


def semantic_chunk(text: str) -> List[str]:
    """
    Split raw text into semantically coherent chunks.
    Uses paragraph-aware splitting with a sliding window fallback.
    """
    paragraphs = _split_into_paragraphs(text)

    chunks: List[str] = []
    current_chunk = ""

    for para in paragraphs:
        # If adding this paragraph stays under target, append
        if len(current_chunk) + len(para) + 2 <= CHUNK_SIZE:
            current_chunk = f"{current_chunk}\n\n{para}".strip() if current_chunk else para
        else:
            # Save current chunk if it meets minimum length
            if len(current_chunk) >= MIN_CHUNK_LENGTH:
                chunks.append(current_chunk)
            # If the paragraph itself is larger than chunk size, do sliding window
            if len(para) > CHUNK_SIZE:
                for i in range(0, len(para), CHUNK_SIZE - CHUNK_OVERLAP):
                    window = para[i:i + CHUNK_SIZE]
                    if len(window) >= MIN_CHUNK_LENGTH:
                        chunks.append(window)
                current_chunk = ""
            else:
                current_chunk = para

    # Don't forget the last chunk
    if current_chunk and len(current_chunk) >= MIN_CHUNK_LENGTH:
        chunks.append(current_chunk)

    log.info(f"Semantic chunking produced {len(chunks)} chunks")
    return chunks


def parse_and_chunk(filename: str, file_bytes: bytes) -> Dict:
    """
    End-to-end: parse a file then semantically chunk it.
    Returns a dict compatible with the vector_db.store_chunks format.
    """
    raw_text = parse_file(filename, file_bytes)
    chunks = semantic_chunk(raw_text)

    return {
        "filename": filename,
        "total_characters": len(raw_text),
        "num_chunks": len(chunks),
        "chunks": [
            {"chunk_text": chunk, "metrics_found": bool(re.search(r'\d+\.?\d*%|\$[\d,.]+|\d{4}', chunk))}
            for chunk in chunks
        ],
    }
