"""
KEEP v2 — Central Config Loader

Loads config.yaml and provides typed access to all thresholds,
budgets, and weights used across the pipeline.
"""

import os
import yaml
from pathlib import Path


_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.yaml"


def _load_config() -> dict:
    """Load YAML config once."""
    with open(_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


_cfg = _load_config()


# ── Pipeline Identity ──────────────────────────────────────
PIPELINE_VERSION: str = _cfg.get("pipeline_version", "v5.0")

# ── Budgets & Circuit Breakers ─────────────────────────────
MAX_LLM_CALLS: int = _cfg.get("max_llm_calls", 10)
LATENCY_BUDGET: dict = _cfg.get("latency_budget_sec", {"search": 4, "extraction": 4, "synthesis": 4})
MAX_REFINEMENT_ATTEMPTS: int = _cfg.get("max_refinement_attempts", 2)

# ── Thresholds ─────────────────────────────────────────────
DEDUP_THRESHOLD: float = _cfg.get("dedup_threshold", 0.88)
VALIDATOR_MIN_SCORE: float = _cfg.get("validator_min_score", 7.0)

# ── Extraction Limits ──────────────────────────────────────
_extractor = _cfg.get("extractor", {})
MAX_CHUNKS_PER_SOURCE: int = _extractor.get("max_chunks_per_source", 3)
MAX_TOKENS_PER_CHUNK: int = _extractor.get("max_tokens_per_chunk", 500)

# ── Source Weights ─────────────────────────────────────────
SOURCE_WEIGHTS: dict = _cfg.get("source_weights", {"paper": 1.2, "docs": 1.0, "blog": 0.6})

# ── LLM Config (Legacy — used as fallback) ─────────────────
LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
LLM_TEMPERATURE: float = 0.0

# ── Hybrid LLM Cost-Routing (Phase 4) ─────────────────────
_routing_cfg = _cfg.get("llm_routing", {})

# Tier definitions
REASONING_TIER: dict = _routing_cfg.get("reasoning", {
    "provider": "google", "model": "gemini-2.5-flash", "temperature": 0.0,
})
CLASSIFICATION_TIER: dict = _routing_cfg.get("classification", {
    "provider": "ollama", "model": "llama3.1:8b",
    "base_url": "http://localhost:11434", "temperature": 0.0,
})

# Fallback config
FALLBACK_CFG: dict = _routing_cfg.get("fallback", {
    "enabled": True, "max_retries": 1,
    "provider": "google", "model": "gemini-2.5-flash",
})

# Agent → tier mapping
AGENT_TIERS: dict = _routing_cfg.get("agent_tiers", {
    "planner": "reasoning", "synthesizer": "reasoning", "verifier": "reasoning",
    "extractor": "classification", "validator": "classification",
})

# Cost per 1M tokens (USD) — for tracking only
COST_PER_MILLION: dict = _routing_cfg.get("cost_per_million_tokens", {
    "gemini-2.5-flash": 0.15, "llama3.1:8b": 0.0,
})
