# KEEP v3 — Future Upgrades & Scaling Plan

This document outlines the strategic roadmap to evolve the KEEP v2 MVP into a real-time, highly scalable enterprise-grade research platform.

## Phase 1: Real-Time Streaming UI (Next.js & React) [COMPLETED]
**Goal:** Transition from a synchronous Streamlit dashboard to a real-time, responsive web application.
- **Architecture:** Initialize a Next.js (TypeScript) frontend. 
- **Backend Bridge:** Expose the LangGraph pipeline via a FastAPI backend.
- **Streaming:** Implement Server-Sent Events (SSE) or WebSockets to stream LangGraph state changes to the UI as they happen.
- **UI Enhancements:** Animated agent cards (e.g., "Search Agent is thinking..."), streaming text for the synthesizer, and an interactive trace timeline.

## Phase 2: Persistent Vector Memory (Pinecone / ChromaDB) [COMPLETED]
**Goal:** Prevent redundant extraction and give the system "long-term memory" across sessions.
- **Implementation:** Replace `diskcache` / `Chroma` with a proper vector database using Pinecone Serverless Integrated Inference.
- **Workflow:** When the Extractor validates chunks of text, upsert them to Pinecone, tagged with their URL.
- **Retrieval:** Before querying external APIs, the Search Agent queries the Vector DB for similar semantic concepts. If high-confidence matches exist, skip external search and save latency.

## Phase 3: Private Document Ingestion (RAG) [COMPLETED]
**Goal:** Allow users to research their own proprietary data alongside public web data.
- **Tool Creation:** Build a `LocalDocumentTool` that parses PDFs, DOCX, and CSV files.
- **Routing:** Update the Planner Agent to classify whether a query requires external web search, internal document search, or a hybrid of both.
- **Chunking:** Implement intelligent semantic chunking for uploaded documents before feeding them to the Extractor.

## Phase 4: Hybrid Cost-Routing (Local Open-Source LLMs) [COMPLETED]
**Goal:** Drastically reduce API costs by routing simple tasks to local models.
- **Infrastructure:** Set up Ollama to run models like `Llama-3-8B` or `Gemma-2-9B` locally.
- **Routing Logic:** 
  - **Planner & Synthesizer:** Continue using high-reasoning cloud models (Gemini 2.5 Flash / GPT-4o).
  - **Extractor & Validator:** Route these high-volume, repetitive classification tasks to the local Llama-3 model.
- **Fallback:** If the local model fails to parse complex syntax, automatically retry with the cloud model.

## Phase 5: Multi-Modal Output & Charting [COMPLETED]
**Goal:** Move beyond text-based synthesis.
- **Data Visualization:** Give the Synthesizer access to a `PythonREPLTool` to generate matplotlib/seaborn charts based on extracted data tables.
- **Export:** Allow the user to export the final synthesized research report as a cleanly formatted PDF or Markdown file containing citations and graphs.
