from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from src.orchestrator.pipeline import build_pipeline
from src.agents.ingestion import ingest_document
from src.tools.document_parser import SUPPORTED_EXTENSIONS
from src.utils.logger import get_logger
from src.utils.llm_router import is_ollama_available, reset_tracker, get_tracker
from src.utils.config import REASONING_TIER, CLASSIFICATION_TIER, AGENT_TIERS

log = get_logger("API")

app = FastAPI(title="KEEP v2 Streaming API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UploadedDocRef(BaseModel):
    filename: str
    doc_url: str
    num_chunks: int

class QueryRequest(BaseModel):
    query: str
    uploaded_docs: Optional[List[UploadedDocRef]] = None
    openai_api_key: Optional[str] = None

workflow = build_pipeline()
pipeline_app = workflow.compile()


# ── Document Upload Endpoint ──────────────────────────────

@app.post("/api/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """
    Upload one or more documents (PDF, DOCX, CSV, TXT).
    Documents are parsed, chunked, and stored in Pinecone VectorDB.
    Returns ingestion metadata for each file.
    """
    log.info(f"Upload request received: {len(files)} file(s)")

    results = []
    for file in files:
        try:
            content = await file.read()
            result = ingest_document(file.filename, content)
            results.append(result)
        except Exception as e:
            log.error(f"Upload failed for {file.filename}: {e}")
            results.append({
                "filename": file.filename,
                "status": "error",
                "message": str(e),
                "num_chunks": 0,
            })

    return JSONResponse(content={"results": results})


@app.get("/api/upload/supported")
async def supported_formats():
    """Return supported file extensions for upload."""
    return {"supported_extensions": sorted(SUPPORTED_EXTENSIONS)}


# ── LLM Routing Health Check ──────────────────────────────

@app.get("/api/llm/status")
async def llm_status():
    """
    Returns the health status of the LLM routing system.
    Checks Ollama availability and reports current tier configuration.
    """
    ollama_up = is_ollama_available()
    return {
        "ollama_available": ollama_up,
        "routing_mode": "hybrid" if ollama_up else "cloud_only",
        "tiers": {
            "reasoning": {
                "provider": REASONING_TIER.get("provider"),
                "model": REASONING_TIER.get("model"),
            },
            "classification": {
                "provider": CLASSIFICATION_TIER.get("provider") if ollama_up else "google (fallback)",
                "model": CLASSIFICATION_TIER.get("model") if ollama_up else REASONING_TIER.get("model"),
            },
        },
        "agent_tiers": AGENT_TIERS,
    }


# ── Research Endpoint (SSE) ───────────────────────────────

@app.post("/api/research")
async def research(req: QueryRequest):
    """
    Starts the KEEP v2 pipeline and streams LangGraph state changes via SSE.
    Supports optional uploaded_docs for hybrid RAG routing.
    """
    log.info(f"Received API query: {req.query}")
    if req.uploaded_docs:
        log.info(f"With {len(req.uploaded_docs)} uploaded document(s)")

    # Convert uploaded_docs to plain dicts for the pipeline
    uploaded_docs_list = []
    if req.uploaded_docs:
        uploaded_docs_list = [d.model_dump() for d in req.uploaded_docs]

    async def event_generator():
        initial_state = {
            "query": req.query,
            "sub_queries": [],
            "search_mode": "web_only",
            "sources": [],
            "validated_sources": [],
            "extracted_data": [],
            "uploaded_docs": uploaded_docs_list,
            "claims": [],
            "final_report": "",
            "confidence": 0.0,
            "llm_call_count": 0,
            "refinement_loops": 0,
            "explainability_log": [],
            "model_usage_log": {},
            "low_evidence_flag": False,
            "no_result_flag": False,
        }
        
        # Set API Key in environment if provided
        if req.openai_api_key:
            os.environ["OPENAI_API_KEY"] = req.openai_api_key
        
        # We use astream to stream graph updates
        try:
            async for output in pipeline_app.astream(initial_state):
                # LangGraph yields a dictionary mapping node names to their output states
                for node_name, state_update in output.items():
                    log.info(f"Node completed: {node_name}")
                    
                    # Prepare SSE payload
                    payload = {
                        "node": node_name,
                        "state_update": state_update
                    }
                    
                    yield f"data: {json.dumps(payload)}\n\n"
                    # Small sleep to allow connections to yield
                    await asyncio.sleep(0.01)
                    
            yield f"data: {json.dumps({'status': 'completed'})}\n\n"
        except Exception as e:
            log.error(f"Pipeline error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            if req.openai_api_key and "OPENAI_API_KEY" in os.environ:
                del os.environ["OPENAI_API_KEY"]

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
