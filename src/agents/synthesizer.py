"""
KEEP v2 — Synthesizer Agent (Probabilistic Layer)

Combines extracted evidence into a structured research report.
Enforces claim-citation binding and handles contradictions honestly.
"""

import json
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage

from src.utils.llm_router import get_llm
from src.tools.chart_generator import generate_chart_base64

from src.utils.logger import get_logger
from src.utils.config import MAX_LLM_CALLS, PIPELINE_VERSION

log = get_logger("SynthesizerAgent")

SYNTHESIZER_SYSTEM_PROMPT = """You are a research synthesis engine. Your job is to produce a grounded research report from extracted evidence.

RULES (strict, non-negotiable):
1. Every single claim you make MUST be backed by a citation from the provided sources.
2. Use inline citations in the format [Source: <url>] after each claim.
3. If two or more sources CONTRADICT each other on a point, you MUST present BOTH viewpoints and tag the section with: "⚠️ Conflicting evidence found"
4. If a claim cannot be supported by any provided source, DO NOT include it. Drop it entirely.
5. Structure the report with clear sections: Summary, Key Findings, Detailed Analysis, Limitations.

Additionally, output a separate JSON block at the end with all claims mapped to citations:

```claims
[
  {"claim": "...", "citation_url": "..."},
  ...
]
```

If you find quantitative, tabular, or comparative data, generate a Python matplotlib code block to visualize it.
Use `plt.savefig(OUTPUT_PATH)` to save the figure.
Example:
```python chart
import matplotlib.pyplot as plt
# setup data
plt.bar(['A', 'B'], [10, 20])
plt.title("Comparison")
plt.savefig(OUTPUT_PATH, bbox_inches='tight')
```

Be thorough, precise, and honest. Never fabricate information.
"""


def synthesizer_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synthesize extracted data into a structured, fully cited research report.
    """
    extracted_data = state.get("extracted_data", [])
    validated_sources = state.get("validated_sources", [])
    query = state.get("query", "")
    llm_call_count = state.get("llm_call_count", 0)
    explainability_log = state.get("explainability_log", [])

    if not extracted_data:
        log.warning("No extracted data to synthesize")
        return {
            **state,
            "final_report": "❌ Unable to generate grounded response — no extractable evidence found.",
            "claims": [],
            "no_result_flag": True,
        }

    # Graceful degradation at budget limit
    if llm_call_count >= MAX_LLM_CALLS:
        log.warning("Circuit breaker: MAX_LLM_CALLS reached — producing minimal synthesis")
        minimal_report = "## Research Summary (Partial — Budget Limit Reached)\n\n"
        for item in extracted_data:
            for chunk in item.get("chunks", []):
                minimal_report += f"- {chunk.get('chunk_text', '')[:200]} [Source: {item['source_url']}]\n"
        return {
            **state,
            "final_report": minimal_report,
            "claims": [],
            "llm_call_count": llm_call_count,
        }

    log.info(f"Synthesizing report from {len(extracted_data)} sources")

    # Build context for the synthesizer
    evidence_text = ""
    for item in extracted_data:
        url = item["source_url"]
        evidence_text += f"\n--- Source: {url} ---\n"
        for chunk in item.get("chunks", []):
            evidence_text += f"  • {chunk.get('chunk_text', '')}\n"

    # Include source metadata for credibility context
    source_meta = ""
    for vs in validated_sources:
        source_meta += (
            f"  - {vs['url'][:80]} | type={vs.get('source_type','unknown')} "
            f"| score={vs.get('final_score','N/A')}\n"
        )

    llm = get_llm("synthesizer")

    response = llm.invoke([
        SystemMessage(content=SYNTHESIZER_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Research Topic: {query}\n\n"
            f"Source Metadata:\n{source_meta}\n\n"
            f"Extracted Evidence:\n{evidence_text}\n\n"
            f"Produce the full research report with inline citations."
        )),
    ])
    llm_call_count += 1

    report_content = response.content.strip()

    # Parse claims JSON block if present
    claims = []
    if "```claims" in report_content:
        try:
            claims_block = report_content.split("```claims")[1].split("```")[0].strip()
            claims = json.loads(claims_block)
        except (json.JSONDecodeError, IndexError) as e:
            log.warning(f"Could not parse claims block: {e}")

    # Remove the claims block from the visible report
    if "```claims" in report_content:
        report_content = report_content.split("```claims")[0].strip()

    # Parse and execute chart block if present
    chart_base64 = None
    if "```python chart" in report_content:
        try:
            chart_code = report_content.split("```python chart")[1].split("```")[0].strip()
            log.info("Chart code detected, generating chart...")
            chart_base64 = generate_chart_base64(chart_code)
        except Exception as e:
            log.warning(f"Error parsing chart code: {e}")
            
    # Remove the chart code block from the visible report
    if "```python chart" in report_content:
        # We replace the whole block (including the closing ```) with the image or empty string
        parts = report_content.split("```python chart")
        before_chart = parts[0]
        after_chart = parts[1].split("```", 1)[1] if "```" in parts[1] else ""
        report_content = before_chart + "\n" + after_chart
        
    # Inject the chart image into the report if successfully generated
    if chart_base64:
        report_content += f"\n\n### Data Visualization\n\n![Generated Chart](data:image/png;base64,{chart_base64})\n"

    log.info(f"Synthesis complete: {len(claims)} claims extracted")

    explainability_log.append({
        "agent": "SynthesizerAgent",
        "action": "synthesis_complete",
        "claims_count": len(claims),
        "report_length": len(report_content),
        "pipeline_version": PIPELINE_VERSION,
    })

    return {
        **state,
        "final_report": report_content,
        "claims": claims,
        "llm_call_count": llm_call_count,
        "explainability_log": explainability_log,
    }
