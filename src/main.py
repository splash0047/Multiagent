"""
KEEP v2 — CLI Entry Point

Run the pipeline from the command line for testing.
Usage: python -m src.main "your research query here"
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')
import json
from dotenv import load_dotenv

load_dotenv()

from src.orchestrator.pipeline import run_pipeline
from src.utils.logger import get_logger

log = get_logger("Main")


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.main \"your research query\"")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    log.info(f"Starting KEEP v2 for query: {query}")

    result = run_pipeline(query)

    # ── Display Results ────────────────────────────────────
    print("\n" + "=" * 70)
    print("📄 KEEP v2 — RESEARCH REPORT")
    print("=" * 70)

    # Flags
    if result.get("no_result_flag"):
        print("\n❌ NO RELIABLE SOURCES FOUND\n")
    elif result.get("low_evidence_flag"):
        print("\n⚠️  LIMITED RELIABLE SOURCES FOUND\n")

    # Report
    print(result.get("final_report", "No report generated."))

    # Confidence
    confidence = result.get("confidence", 0.0)
    print(f"\n{'─' * 40}")
    print(f"🎯 Confidence Score: {confidence}")

    # Sources
    validated = result.get("validated_sources", [])
    if validated:
        print(f"\n📚 Validated Sources ({len(validated)}):")
        for v in validated:
            print(
                f"  • [{v.get('source_type', '?')}] {v.get('title', 'Untitled')[:60]}"
                f" | score={v.get('final_score', 'N/A')}"
            )
            print(f"    {v.get('url', '')}")

    # Verified claims count
    claims = result.get("claims", [])
    print(f"\n✅ Verified Claims: {len(claims)}")

    # Pipeline stats
    print(f"\n📊 Pipeline Stats:")
    print(f"  LLM calls: {result.get('llm_call_count', 0)}")
    print(f"  Refinement loops: {result.get('refinement_loops', 0)}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
