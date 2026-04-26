from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal

# ---------------------------------------------------------
# Core Data Models (Strict Enforcements)
# ---------------------------------------------------------

class Source(BaseModel):
    title: str = Field(description="Title of the source document.")
    url: str = Field(description="Direct URL to the source.")
    source_type: Literal["paper", "blog", "docs"] = Field(description="Categorization of the source type.")
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

# ---------------------------------------------------------
# Orchestration State Model
# ---------------------------------------------------------

class ResearchState(BaseModel):
    query: str
    sub_queries: List[str] = Field(default_factory=list)
    sources: List[Source] = Field(default_factory=list)
    validated_sources: List[ValidatedSource] = Field(default_factory=list)
    extracted_data: List[ExtractedData] = Field(default_factory=list)
    
    # Synthesis & Verification
    claims: List[Claim] = Field(default_factory=list)
    final_report: str = ""
    
    # System Control & Explainability
    llm_call_count: int = Field(default=0)
    refinement_loops: int = Field(default=0)
    explainability_log: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Flags
    low_evidence_flag: bool = Field(default=False)
    no_result_flag: bool = Field(default=False)
