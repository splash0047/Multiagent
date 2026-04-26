"""
KEEP v2 — Adversarial Test Suite

This script explicitly tests the system against the requested edge-case scenarios:
1. Vague queries
2. Misleading topics
3. Empty results (No-hit queries)
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
import logging
from dotenv import load_dotenv

load_dotenv()

from src.orchestrator.pipeline import run_pipeline
from src.utils.logger import get_logger

# Mute noisy third-party logs for clean testing output
logging.getLogger("httpx").setLevel(logging.WARNING)

def run_test_scenario(scenario_name: str, query: str):
    print("\n" + "=" * 80)
    print(f"🧪 SCENARIO: {scenario_name}")
    print(f"   Query: '{query}'")
    print("=" * 80)
    
    result = run_pipeline(query)
    
    print("\n--- TEST RESULTS ---")
    
    # Check flags
    if result.get("no_result_flag"):
        print("🚩 FLAG TRIGGERED: No Result Flag")
    if result.get("low_evidence_flag"):
        print("🚩 FLAG TRIGGERED: Low Evidence Flag")
        
    print(f"📊 Confidence Score:  {result.get('confidence', 0.0)}")
    print(f"📚 Validated Sources: {len(result.get('validated_sources', []))}")
    print(f"✅ Verified Claims:   {len(result.get('claims', []))}")
    print(f"🤖 LLM Calls:         {result.get('llm_call_count', 0)}")
    
    print("\n--- FINAL REPORT ---")
    report = result.get("final_report", "")
    # Print just a snippet if it's too long
    if len(report) > 500:
        print(report[:500] + "...\n[Report Truncated]")
    else:
        print(report)

def main():
    scenarios = [
        {
            "name": "1. Vague Query",
            "query": "stuff about AI"
        },
        {
            "name": "2. Misleading / Fictional Topic",
            "query": "evidence that the earth is completely flat and made of blue cheese 2024 studies"
        },
        {
            "name": "3. Empty Results (Gibberish)",
            "query": "asdfjklqweruiopzxcvbnm1234567890 testing string impossible to find"
        },
        {
            "name": "4. Valid Query (Control)",
            "query": "impact of retrieval augmented generation on hallucination reduction in LLMs 2023-2025"
        }
    ]
    
    for s in scenarios:
        run_test_scenario(s["name"], s["query"])

if __name__ == "__main__":
    main()
