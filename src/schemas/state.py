from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Optional

# ---------------------------------------------------------
# Core Data Models (Strict Enforcements)
# ---------------------------------------------------------

class Source(BaseModel):
    title: str = Field(description="Title of the source document.")
    url: str = Field(description="Direct URL to the source.")
    source_type: Literal["paper", "blog", "docs", "memory"] = Field(description="Categorization of the source type.")
    snippet: str = Field(description="Brief text snippet returned by the search engine.")

class ValidatedSource(Source):
    credibility_score: float = Field(ge=0.0, le=10.0)
    recency_score: float = Field(ge=0.0, le=10.0)
    depth_score: float = Field(ge=0.0, le=10.0)
    final_score: float = Field(ge=0.0, le=10.0, description="Weighted score determining if source is kept.")

class ExtractedChunk(BaseModel):
    chunk_text: str
    metrics_found: bool = Field(default=False, description="True if numeric facts/metrics exist in this chunk.")

class ExtractedData(BaseModel):
    source_url: str
    chunks: List[ExtractedChunk]
    coverage_ratio: float = Field(ge=0.0, le=1.0, description="extracted_chunks / total_chunks")

class Claim(BaseModel):
    claim_text: str
    citation_url: str = Field(description="MUST match a URL from validated_sources.")

class UploadedDoc(BaseModel):
    """Metadata for an uploaded private document."""
    filename: str
    doc_url: str = Field(description="Internal URL like local://filename#id")
    num_chunks: int = Field(default=0)

# ---------------------------------------------------------
# Orchestration State Model
# ---------------------------------------------------------

class ResearchState(BaseModel):
    query: str
    sub_queries: List[str] = Field(default_factory=list)
    search_mode: Literal["web_only", "local_only", "hybrid"] = Field(default="web_only")
    sources: List[Source] = Field(default_factory=list)
    validated_sources: List[ValidatedSource] = Field(default_factory=list)
    extracted_data: List[ExtractedData] = Field(default_factory=list)
    
    # Private Document Ingestion (RAG)
    uploaded_docs: List[UploadedDoc] = Field(default_factory=list)
    
    # Synthesis & Verification
    claims: List[Claim] = Field(default_factory=list)
    final_report: str = ""
    
    # System Control & Explainability
    llm_call_count: int = Field(default=0)
    refinement_loops: int = Field(default=0)
    explainability_log: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Cost Routing Analytics (Phase 4)
    model_usage_log: Dict[str, Any] = Field(default_factory=dict, description="LLM routing stats: cloud vs local calls, fallbacks, cost savings.")
    
    # Flags
    low_evidence_flag: bool = Field(default=False)
    no_result_flag: bool = Field(default=False)

