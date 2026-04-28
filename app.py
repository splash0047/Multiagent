"""
KEEP v2 — Streamlit UI (MVP)

Premium research interface with:
- Agent activity timeline
- Source confidence breakdown
- Trace replay
- Partial failure visibility
- LLM Cost-Routing analytics (Phase 4)
"""

import streamlit as st
import time
import json
from dotenv import load_dotenv

load_dotenv()

from src.orchestrator.pipeline import run_pipeline
from src.utils.llm_router import is_ollama_available
from src.utils.config import AGENT_TIERS, REASONING_TIER, CLASSIFICATION_TIER
from src.utils.export import export_to_markdown, export_to_pdf

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
    .stApp { font-family: 'Inter', sans-serif; }
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-size: 2.8rem; font-weight: 700; text-align: center; margin-bottom: 0.2rem;
    }
    .sub-header { text-align: center; color: #888; font-size: 1rem; margin-bottom: 2rem; }
    .source-card {
        background: #0e1117; border: 1px solid #333; border-radius: 10px;
        padding: 1rem; margin-bottom: 0.8rem; transition: border-color 0.3s ease;
    }
    .source-card:hover { border-color: #667eea; }
    .pipeline-step {
        display: inline-block; padding: 0.3rem 0.8rem; border-radius: 20px;
        font-size: 0.8rem; margin: 0.2rem; font-weight: 500;
    }
    .step-pending { background: #33333344; color: #888; border: 1px solid #555; }
    .routing-badge {
        display: inline-block; padding: 0.2rem 0.6rem; border-radius: 12px;
        font-size: 0.75rem; font-weight: 600;
    }
    .badge-cloud { background: #667eea22; color: #667eea; border: 1px solid #667eea; }
    .badge-local { background: #00d26a22; color: #00d26a; border: 1px solid #00d26a; }
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

    # LLM Routing Status
    st.markdown("### 🔀 LLM Routing")
    ollama_up = is_ollama_available()
    if ollama_up:
        st.success("🟢 Ollama Online — Hybrid Mode")
        st.caption(f"Local: {CLASSIFICATION_TIER.get('model', 'N/A')}")
    else:
        st.warning("🟡 Ollama Offline — Cloud Only")
    st.caption(f"Cloud: {REASONING_TIER.get('model', 'N/A')}")
    st.divider()

    # Agent tier assignments
    st.markdown("### 🎯 Agent Tiers")
    for agent, tier in AGENT_TIERS.items():
        icon = "☁️" if tier == "reasoning" else "🖥️"
        st.markdown(f"{icon} **{agent.capitalize()}** → {tier}")
    st.divider()

    st.markdown("### 🏗️ Architecture")
    for s in ["Planner", "Search", "Validator", "Extractor", "Synthesizer", "Verifier", "Confidence"]:
        st.markdown(f"<span class='pipeline-step step-pending'>{s}</span>", unsafe_allow_html=True)

# ── Main Input ─────────────────────────────────────────────
col1, col2 = st.columns([4, 1])
with col1:
    query = st.text_input("🔍 Research Query", placeholder="e.g., Impact of RAG on LLM accuracy 2023-2025", label_visibility="collapsed")
with col2:
    run_btn = st.button("🚀 Research", use_container_width=True, type="primary")

# ── Execution ──────────────────────────────────────────────
if run_btn and query:
    progress_bar = st.progress(0)
    status_text = st.empty()

    for text, pct in [("🧠 Planning...", 10), ("🔍 Searching...", 30)]:
        status_text.markdown(f"**{text}**")
        progress_bar.progress(pct)
        time.sleep(0.3)

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
    usage = result.get("model_usage_log", {})
    m1, m2, m3, m4, m5 = st.columns(5)
    confidence = result.get("confidence", 0.0)

    with m1:
        st.metric("🎯 Confidence", f"{confidence:.1%}")
    with m2:
        st.metric("📚 Sources", len(result.get("validated_sources", [])))
    with m3:
        st.metric("✅ Claims", len(result.get("claims", [])))
    with m4:
        st.metric("⚡ Latency", f"{elapsed}s")
    with m5:
        st.metric("💰 Savings", f"{usage.get('cost_savings_pct', 0):.0f}%")

    if result.get("no_result_flag"):
        st.error("❌ No reliable sources found.")
    elif result.get("low_evidence_flag"):
        st.warning("⚠️ Limited reliable sources — confidence may be lower.")

    st.divider()

    # ── Tabs ───────────────────────────────────────────────
    tab_report, tab_sources, tab_routing, tab_trace = st.tabs([
        "📄 Report", "📚 Sources", "🔀 Cost Routing", "🔍 Trace"
    ])

    with tab_report:
        st.markdown(result.get("final_report", "No report generated."))
        claims = result.get("claims", [])
        if claims:
            with st.expander(f"✅ Verified Claims ({len(claims)})"):
                for i, c in enumerate(claims):
                    st.markdown(f"**{i+1}.** {c.get('claim_text', c.get('claim', ''))}")
                    st.caption(f"📎 {c.get('citation_url', c.get('citation', ''))}")
                    
        # ── Export Buttons ─────────────────────────────────────
        st.divider()
        st.markdown("### 📥 Export Report")
        col_export1, col_export2 = st.columns(2)
        
        report_text = result.get("final_report", "")
        
        with col_export1:
            st.download_button(
                label="📄 Download as Markdown",
                data=export_to_markdown(report_text),
                file_name="KEEP_Research_Report.md",
                mime="text/markdown",
                use_container_width=True
            )
            
        with col_export2:
            pdf_bytes = export_to_pdf(report_text)
            if pdf_bytes:
                st.download_button(
                    label="📕 Download as PDF",
                    data=pdf_bytes,
                    file_name="KEEP_Research_Report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.error("Failed to generate PDF.")

    with tab_sources:
        validated = result.get("validated_sources", [])
        if validated:
            for v in validated:
                st.markdown(f"""<div class="source-card">
                    <strong>{v.get('title', 'Untitled')[:80]}</strong><br>
                    <small>🏷️ {v.get('source_type', 'unknown')} | 🎯 Score: {v.get('final_score', 'N/A')}</small><br>
                    <a href="{v.get('url', '#')}" target="_blank">{v.get('url', '')[:80]}</a>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No validated sources.")

    with tab_routing:
        st.markdown("### 🔀 LLM Cost-Routing Analytics")
        if usage:
            rc1, rc2, rc3, rc4 = st.columns(4)
            with rc1:
                st.metric("☁️ Cloud Calls", usage.get("cloud_calls", 0))
            with rc2:
                st.metric("🖥️ Local Calls", usage.get("local_calls", 0))
            with rc3:
                st.metric("⚠️ Fallbacks", usage.get("fallback_triggers", 0))
            with rc4:
                st.metric("⏱️ LLM Time", f"{usage.get('total_latency_ms', 0):.0f}ms")
            st.divider()
            cc1, cc2 = st.columns(2)
            with cc1:
                st.markdown("#### 💰 Cost Comparison")
                st.markdown(f"| Metric | Value |\n|--------|-------|\n"
                    f"| Actual Cost | ${usage.get('estimated_cost_usd', 0):.6f} |\n"
                    f"| All-Cloud Cost | ${usage.get('hypothetical_all_cloud_cost_usd', 0):.6f} |\n"
                    f"| **Savings** | **{usage.get('cost_savings_pct', 0):.1f}%** |")
            with cc2:
                st.markdown("#### 🎯 Tier Assignments")
                for agent, tier in AGENT_TIERS.items():
                    bc = "badge-local" if tier == "classification" else "badge-cloud"
                    lb = "LOCAL" if tier == "classification" else "CLOUD"
                    st.markdown(f"**{agent.capitalize()}** → <span class='routing-badge {bc}'>{lb}</span>", unsafe_allow_html=True)
            with st.expander("📋 Raw Routing Data"):
                st.json(usage)
        else:
            st.info("No routing data available.")

    with tab_trace:
        st.markdown("### 🔍 Pipeline Trace Replay")
        logs = result.get("explainability_log", [])
        if logs:
            for entry in logs:
                agent = entry.get("agent", "Unknown")
                action = entry.get("action", "")
                icon = {"PlannerAgent": "🧠", "SearchAgent": "🔍", "ValidatorAgent": "✅",
                        "ExtractorAgent": "📊", "SynthesizerAgent": "📝",
                        "CitationVerifier": "🔒", "ConfidenceEngine": "🎯"}.get(agent, "⚙️")
                with st.expander(f"{icon} {agent} → {action}"):
                    st.json(entry)
        else:
            st.info("No trace logs available.")

        st.markdown("### 📊 Pipeline Statistics")
        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.metric("LLM Calls", result.get("llm_call_count", 0))
        with sc2:
            st.metric("Refinements", result.get("refinement_loops", 0))
        with sc3:
            st.metric("Mode", "Hybrid" if usage.get("local_calls", 0) > 0 else "Cloud Only")

elif run_btn and not query:
    st.warning("Please enter a research query.")
