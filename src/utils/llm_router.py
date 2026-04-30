"""
KEEP v2 — Hybrid LLM Router (Phase 4)

Central factory for LLM instances with two-tier cost routing:
  - "reasoning"       → Cloud Gemini (Planner, Synthesizer, Verifier)
  - "classification"  → Local Ollama (Extractor, Validator)

Automatic fallback: if the local model fails, retries with cloud.
Tracks every call for cost analysis.
"""

import time
from typing import Literal, Optional, List, Dict, Any
from dataclasses import dataclass, field

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage

from src.utils.logger import get_logger
from src.utils.config import (
    REASONING_TIER, CLASSIFICATION_TIER,
    FALLBACK_CFG, AGENT_TIERS, COST_PER_MILLION,
)

log = get_logger("LLMRouter")

# ── Tier type ──────────────────────────────────────────────
Tier = Literal["reasoning", "classification"]


# ── Usage Tracking ─────────────────────────────────────────

@dataclass
class LLMCallRecord:
    agent: str
    tier: str
    model: str
    provider: str
    latency_ms: float
    fallback_used: bool = False
    error: Optional[str] = None


class UsageTracker:
    """Thread-safe accumulator for per-pipeline-run model usage stats."""

    def __init__(self):
        self.records: List[LLMCallRecord] = []

    def log_call(self, record: LLMCallRecord):
        self.records.append(record)

    def summary(self) -> Dict[str, Any]:
        """Return a compact summary for the explainability log."""
        cloud_calls = sum(1 for r in self.records if r.provider == "google")
        local_calls = sum(1 for r in self.records if r.provider == "ollama")
        fallbacks = sum(1 for r in self.records if r.fallback_used)
        total_latency = sum(r.latency_ms for r in self.records)

        # Estimate savings: if all calls went to cloud vs actual
        cloud_model = REASONING_TIER.get("model", "gemini-2.5-flash")
        cloud_cost_rate = COST_PER_MILLION.get(cloud_model, 0.15)
        # Rough token estimate: ~500 tokens per call (conservative)
        tokens_per_call = 500
        hypothetical_cloud_cost = len(self.records) * tokens_per_call * cloud_cost_rate / 1_000_000
        actual_cost = cloud_calls * tokens_per_call * cloud_cost_rate / 1_000_000

        return {
            "total_llm_calls": len(self.records),
            "cloud_calls": cloud_calls,
            "local_calls": local_calls,
            "fallback_triggers": fallbacks,
            "total_latency_ms": round(total_latency, 1),
            "estimated_cost_usd": round(actual_cost, 6),
            "hypothetical_all_cloud_cost_usd": round(hypothetical_cloud_cost, 6),
            "cost_savings_pct": round(
                (1 - actual_cost / hypothetical_cloud_cost) * 100, 1
            ) if hypothetical_cloud_cost > 0 else 0.0,
        }


# Module-level tracker — reset per pipeline run
_tracker = UsageTracker()


def reset_tracker():
    """Reset the usage tracker. Call at pipeline start."""
    global _tracker
    _tracker = UsageTracker()


def get_tracker() -> UsageTracker:
    return _tracker


# ── Ollama Availability Check ──────────────────────────────

def is_ollama_available() -> bool:
    """Check if the Ollama server is reachable."""
    import urllib.request
    base_url = CLASSIFICATION_TIER.get("base_url", "http://localhost:11434")
    try:
        req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


# ── LLM Factory ────────────────────────────────────────────

def _build_ollama_llm(model: str, base_url: str, temperature: float):
    """Lazy import to avoid hard dependency if Ollama not installed."""
    try:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model,
            base_url=base_url,
            temperature=temperature,
            format="json",  # Force JSON mode for structured output
        )
    except ImportError:
        log.warning("langchain-ollama not installed — falling back to cloud")
        return None


def _build_cloud_llm(model: str, temperature: float):
    """Build a Cloud LLM instance (OpenAI or Google). Returns (llm, actual_model, provider)."""
    import os
    if os.environ.get("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        openai_model = "gpt-4o"
        return ChatOpenAI(model=openai_model, temperature=temperature), openai_model, "openai"
    
    return ChatGoogleGenerativeAI(model=model, temperature=temperature), model, "google"


def get_llm(agent_name: str):
    """
    Return the appropriate LLM instance for a given agent.

    Uses the agent_tiers mapping from config.yaml to determine
    whether to use cloud (reasoning) or local (classification).
    """
    tier = AGENT_TIERS.get(agent_name, "reasoning")

    if tier == "classification":
        cfg = CLASSIFICATION_TIER
        provider = cfg.get("provider", "ollama")
        model = cfg.get("model", "llama3.1:8b")
        base_url = cfg.get("base_url", "http://localhost:11434")
        temp = cfg.get("temperature", 0.0)

        if provider == "ollama" and is_ollama_available():
            llm = _build_ollama_llm(model, base_url, temp)
            if llm is not None:
                log.info(f"[{agent_name}] → LOCAL Ollama ({model})")
                return _RoutedLLM(llm, agent_name, tier, model, "ollama")

        # Ollama not available — fall through to cloud
        log.warning(f"[{agent_name}] Ollama unavailable — using cloud fallback")
        cfg = REASONING_TIER

    # Reasoning tier (or fallback)
    cfg = REASONING_TIER
    model = cfg.get("model", "gemini-2.5-flash")
    temp = cfg.get("temperature", 0.0)
    llm, actual_model, provider = _build_cloud_llm(model, temp)
    log.info(f"[{agent_name}] → CLOUD {provider} ({actual_model})")
    return _RoutedLLM(llm, agent_name, tier, actual_model, provider)


# ── Routed LLM Wrapper ────────────────────────────────────

class _RoutedLLM:
    """
    Wraps an LLM with:
      1. Usage tracking (latency, model, provider)
      2. Automatic cloud fallback on failure
    """

    def __init__(self, llm, agent_name: str, tier: str, model: str, provider: str):
        self._llm = llm
        self._agent_name = agent_name
        self._tier = tier
        self._model = model
        self._provider = provider

    def invoke(self, messages: List[BaseMessage], **kwargs):
        """Invoke with tracking, automatic retries for rate limits, and fallback."""
        max_retries = 3
        
        for attempt in range(max_retries):
            start = time.perf_counter()
            try:
                result = self._llm.invoke(messages, **kwargs)
                latency = (time.perf_counter() - start) * 1000

                _tracker.log_call(LLMCallRecord(
                    agent=self._agent_name,
                    tier=self._tier,
                    model=self._model,
                    provider=self._provider,
                    latency_ms=round(latency, 1),
                ))
                return result

            except Exception as e:
                latency = (time.perf_counter() - start) * 1000
                err_str = str(e).lower()
                
                # Check for rate limit or server overloaded (503, 429)
                is_transient = "503" in err_str or "429" in err_str or "temporarily" in err_str or "resource exhausted" in err_str
                
                if is_transient and attempt < max_retries - 1:
                    sleep_time = 2 ** attempt
                    log.warning(
                        f"[{self._agent_name}] {self._provider}/{self._model} overloaded. "
                        f"Retrying in {sleep_time}s... (Attempt {attempt+1}/{max_retries})"
                    )
                    import time as tm
                    tm.sleep(sleep_time)
                    continue
                    
                log.error(
                    f"[{self._agent_name}] {self._provider}/{self._model} FAILED "
                    f"({latency:.0f}ms): {e}"
                )

                # Attempt cloud fallback if this was a local call
                if self._provider == "ollama" and FALLBACK_CFG.get("enabled", True):
                    log.info(f"[{self._agent_name}] Retrying with cloud fallback...")
                    fallback_model = FALLBACK_CFG.get("model", "gemini-2.5-flash")
                    fallback_llm, actual_fb_model, fb_provider = _build_cloud_llm(
                        fallback_model,
                        REASONING_TIER.get("temperature", 0.0),
                    )

                    start_fb = time.perf_counter()
                    try:
                        result = fallback_llm.invoke(messages, **kwargs)
                        fb_latency = (time.perf_counter() - start_fb) * 1000

                        _tracker.log_call(LLMCallRecord(
                            agent=self._agent_name,
                            tier=self._tier,
                            model=actual_fb_model,
                            provider=fb_provider,
                            latency_ms=round(fb_latency, 1),
                            fallback_used=True,
                            error=str(e),
                        ))
                        log.info(
                            f"[{self._agent_name}] Cloud fallback succeeded ({fb_latency:.0f}ms)"
                        )
                        return result
                    except Exception as fb_e:
                        log.error(f"[{self._agent_name}] Cloud fallback ALSO failed: {fb_e}")
                        raise fb_e

                # No fallback possible — re-raise
                _tracker.log_call(LLMCallRecord(
                    agent=self._agent_name,
                    tier=self._tier,
                    model=self._model,
                    provider=self._provider,
                    latency_ms=round(latency, 1),
                    error=str(e),
                ))
                raise
