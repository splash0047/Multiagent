"""
KEEP v2 — Streamlit UI (MVP)

Premium research interface with:
- Agent activity timeline
- Source confidence breakdown
- Trace replay
- Partial failure visibility
"""

import streamlit as st
import time
import json
from dotenv import load_dotenv

load_dotenv()

from src.orchestrator.pipeline import run_pipeline

# ── Page Config ────────────────────────────────────────────
st.set_page_config(
    page_title="KEEP v2 — Citation Research Engine",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif;
    }

    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 0.2rem;
    }

    .sub-header {
        text-align: center;
        color: #888;
        font-size: 1rem;
        margin-bottom: 2rem;
    }

    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 12px;
        padding: 1.2rem;
        border: 1px solid #333;
        margin-bottom: 1rem;
    }

    .source-card {
        background: #0e1117;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        transition: border-color 0.3s ease;
    }

    .source-card:hover {
        border-color: #667eea;
    }

    .confidence-high { color: #00d26a; }
    .confidence-mid { color: #ffc107; }
    .confidence-low { color: #ff4444; }

    .pipeline-step {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin: 0.2rem;
        font-weight: 500;
    }

    .step-active { background: #667eea33; color: #667eea; border: 1px solid #667eea; }
    .step-done { background: #00d26a22; color: #00d26a; border: 1px solid #00d26a; }
    .step-pending { background: #33333344; color: #888; border: 1px solid #555; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────
st.markdown('<h1 class="main-header">🔬 KEEP v2</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Multi-Agent Citation Research Engine — Every claim grounded, every source verified.</p>', unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Pipeline Settings")
    st.caption("Pipeline Version: v5.0 (Locked)")
    st.divider()
    st.markdown("### 🏗️ Architecture")
    steps = [
        "Planner", "Query Refinement", "Parallel Search",
        "Validator", "Deduplication", "Extractor",
        "Synthesizer", "Citation Verifier", "Confidence Engine",
    ]
    for s in steps:
        st.markdown(f"<span class='pipeline-step step-pending'>{s}</span>", unsafe_allow_html=True)

# ── Main Input ─────────────────────────────────────────────
col1, col2 = st.columns([4, 1])
with col1:
    query = st.text_input(
        "🔍 Research Query",
        placeholder="e.g., Impact of retrieval-augmented generation on LLM accuracy 2023-2025",
        label_visibility="collapsed",
    )
with col2:
    run_btn = st.button("🚀 Research", use_container_width=True, type="primary")

# ── Execution ──────────────────────────────────────────────
if run_btn and query:
    # Progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()

    pipeline_steps = [
        ("🧠 Planning sub-queries...", 10),
        ("🔍 Searching across Tavily, arXiv, DDG...", 30),
        ("✅ Validating sources...", 50),
        ("📊 Extracting evidence...", 65),
        ("📝 Synthesizing report...", 80),
        ("🔒 Verifying citations...", 90),
        ("🎯 Computing confidence...", 95),
    ]

    # Simulate progress visualization while pipeline runs
    for step_text, pct in pipeline_steps[:2]:
        status_text.markdown(f"**{step_text}**")
        progress_bar.progress(pct)
        time.sleep(0.3)

    # Run the actual pipeline
    status_text.markdown("**⚡ Running full pipeline...**")
    start_time = time.time()

    try:
        result = run_pipeline(query)
        elapsed = round(time.time() - start_time, 2)

        progress_bar.progress(100)
        status_text.markdown(f"**✅ Complete in {elapsed}s**")

    except Exception as e:
        st.error(f"❌ Pipeline failed: {e}")
        st.stop()

    st.divider()

    # ── Metrics Row ────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    confidence = result.get("confidence", 0.0)
    conf_class = "confidence-high" if confidence >= 0.7 else "confidence-mid" if confidence >= 0.4 else "confidence-low"

    with m1:
        st.metric("🎯 Confidence", f"{confidence:.1%}")
    with m2:
        st.metric("📚 Sources", len(result.get("validated_sources", [])))
    with m3:
        st.metric("✅ Verified Claims", len(result.get("claims", [])))
    with m4:
        st.metric("⚡ Latency", f"{elapsed}s")

    # ── Flags ──────────────────────────────────────────────
    if result.get("no_result_flag"):
        st.error("❌ Unable to generate grounded response — no reliable sources found.")
    elif result.get("low_evidence_flag"):
        st.warning("⚠️ Limited reliable sources found — confidence may be lower.")

    st.divider()

    # ── Report ─────────────────────────────────────────────
    tab_report, tab_sources, tab_trace = st.tabs(["📄 Research Report", "📚 Sources", "🔍 Trace Replay"])

    with tab_report:
        st.markdown(result.get("final_report", "No report generated."))

        # Verified claims
        claims = result.get("claims", [])
        if claims:
            with st.expander(f"✅ Verified Claims ({len(claims)})", expanded=False):
                for i, c in enumerate(claims):
                    claim_text = c.get("claim_text", c.get("claim", ""))
                    url = c.get("citation_url", c.get("citation", ""))
                    st.markdown(f"**{i+1}.** {claim_text}")
                    st.caption(f"📎 {url}")

    with tab_sources:
        validated = result.get("validated_sources", [])
        if validated:
            for v in validated:
                with st.container():
                    st.markdown(f"""
                    <div class="source-card">
                        <strong>{v.get('title', 'Untitled')[:80]}</strong><br>
                        <small>🏷️ {v.get('source_type', 'unknown')} | 🎯 Score: {v.get('final_score', 'N/A')}</small><br>
                        <small>📊 Credibility: {v.get('credibility_score', '-')} | Recency: {v.get('recency_score', '-')} | Depth: {v.get('depth_score', '-')}</small><br>
                        <a href="{v.get('url', '#')}" target="_blank">{v.get('url', '')[:80]}</a>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No validated sources.")

    with tab_trace:
        st.markdown("### 🔍 See How This Answer Was Built")
        st.caption("Full pipeline trace replay — every decision logged.")

        logs = result.get("explainability_log", [])
        if logs:
            for entry in logs:
                agent = entry.get("agent", "Unknown")
                action = entry.get("action", "")
                icon = {
                    "PlannerAgent": "🧠",
                    "SearchAgent": "🔍",
                    "ValidatorAgent": "✅",
                    "ExtractorAgent": "📊",
                    "SynthesizerAgent": "📝",
                    "CitationVerifier": "🔒",
                    "ConfidenceEngine": "🎯",
                }.get(agent, "⚙️")

                with st.expander(f"{icon} {agent} → {action}"):
                    st.json(entry)
        else:
            st.info("No trace logs available.")

        # Pipeline stats
        st.markdown("### 📊 Pipeline Statistics")
        stats_col1, stats_col2 = st.columns(2)
        with stats_col1:
            st.metric("LLM Calls", result.get("llm_call_count", 0))
        with stats_col2:
            st.metric("Refinement Loops", result.get("refinement_loops", 0))

elif run_btn and not query:
    st.warning("Please enter a research query.")
