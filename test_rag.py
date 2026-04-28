import os
import json
from dotenv import load_dotenv

load_dotenv()

from src.agents.ingestion import ingest_document
from src.orchestrator.pipeline import run_pipeline

def test_hybrid_rag():
    print("1. Creating dummy private document...")
    fake_doc_content = b"""
PROJECT POLARIS CONFIDENTIAL REPORT

Overview:
Project Polaris is a top-secret initiative by Acme Corp to develop a new solid-state battery for electric vehicles.
The breakthrough was achieved by using a novel silicon-graphene composite anode.

Key Metrics:
- Energy density: 500 Wh/kg
- Charge time: 10 minutes to 80%
- Expected launch date: Q4 2027

Cost Analysis:
The estimated manufacturing cost is $65 per kWh, making it highly competitive with existing lithium-ion solutions.
"""
    
    print("2. Ingesting document...")
    result = ingest_document("polaris_report.txt", fake_doc_content)
    print(f"Ingestion result: {json.dumps(result, indent=2)}")
    
    if result["status"] != "success":
        print("Ingestion failed. Aborting test.")
        return
        
    print("\n3. Running pipeline with query 'What is the launch date and energy density of Project Polaris?'")
    uploaded_docs = [
        {
            "filename": result["filename"],
            "doc_url": result["doc_url"],
            "num_chunks": result["num_chunks"]
        }
    ]
    
    final_state = run_pipeline("What is the launch date and energy density of Project Polaris?", uploaded_docs=uploaded_docs)
    
    print("\n--- FINAL REPORT ---")
    print(final_state.get("final_report", "No report generated."))
    
    print("\n--- VALIDATED SOURCES ---")
    for src in final_state.get("validated_sources", []):
        print(f"- {src.title} ({src.url})")

if __name__ == "__main__":
    test_hybrid_rag()
