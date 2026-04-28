"""
KEEP v2 — Phase 4 Routing Validation Tests

Tests the LLM router, tier assignments, fallback logic,
and usage tracker without making real LLM calls.
"""

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()


def test_config_loading():
    """Verify all Phase 4 config values load correctly."""
    from src.utils.config import (
        REASONING_TIER, CLASSIFICATION_TIER,
        FALLBACK_CFG, AGENT_TIERS, COST_PER_MILLION,
    )
    
    assert REASONING_TIER["provider"] == "google", "Reasoning tier should use Google"
    assert "gemini" in REASONING_TIER["model"], "Reasoning model should be Gemini"
    
    assert CLASSIFICATION_TIER["provider"] == "ollama", "Classification tier should use Ollama"
    assert "llama" in CLASSIFICATION_TIER["model"], "Classification model should be Llama"
    
    assert FALLBACK_CFG["enabled"] is True, "Fallback should be enabled"
    
    # Verify agent tier mapping
    assert AGENT_TIERS["planner"] == "reasoning"
    assert AGENT_TIERS["synthesizer"] == "reasoning"
    assert AGENT_TIERS["verifier"] == "reasoning"
    assert AGENT_TIERS["extractor"] == "classification"
    assert AGENT_TIERS["validator"] == "classification"
    
    # Cost tracking
    assert COST_PER_MILLION.get("llama3.1:8b", -1) == 0.0, "Local model should be free"
    assert COST_PER_MILLION.get("gemini-2.5-flash", 0) > 0, "Cloud model should have cost"
    
    print("✅ Config loading: PASSED")


def test_usage_tracker():
    """Verify the usage tracker accumulates and summarizes correctly."""
    from src.utils.llm_router import UsageTracker, LLMCallRecord
    
    tracker = UsageTracker()
    
    # Simulate mixed calls
    tracker.log_call(LLMCallRecord(
        agent="planner", tier="reasoning", model="gemini-2.5-flash",
        provider="google", latency_ms=500.0,
    ))
    tracker.log_call(LLMCallRecord(
        agent="extractor", tier="classification", model="llama3.1:8b",
        provider="ollama", latency_ms=200.0,
    ))
    tracker.log_call(LLMCallRecord(
        agent="validator", tier="classification", model="gemini-2.5-flash",
        provider="google", latency_ms=450.0, fallback_used=True, error="Ollama timeout",
    ))
    
    summary = tracker.summary()
    
    assert summary["total_llm_calls"] == 3
    assert summary["cloud_calls"] == 2  # planner + validator fallback
    assert summary["local_calls"] == 1  # extractor
    assert summary["fallback_triggers"] == 1  # validator
    assert summary["total_latency_ms"] == 1150.0
    assert summary["cost_savings_pct"] > 0, "Should show savings from local calls"
    
    print("✅ Usage tracker: PASSED")


def test_tracker_reset():
    """Verify tracker resets between pipeline runs."""
    from src.utils.llm_router import reset_tracker, get_tracker, LLMCallRecord
    
    # Add a record
    get_tracker().log_call(LLMCallRecord(
        agent="test", tier="reasoning", model="test", provider="google", latency_ms=100.0,
    ))
    assert len(get_tracker().records) > 0
    
    # Reset
    reset_tracker()
    assert len(get_tracker().records) == 0
    
    print("✅ Tracker reset: PASSED")


def test_ollama_check():
    """Test Ollama availability check (non-blocking)."""
    from src.utils.llm_router import is_ollama_available
    
    result = is_ollama_available()
    # This is a connectivity check — may be True or False depending on local setup
    assert isinstance(result, bool), "Should return a boolean"
    
    if result:
        print("✅ Ollama check: PASSED (Ollama is ONLINE)")
    else:
        print("✅ Ollama check: PASSED (Ollama is OFFLINE — cloud fallback will be used)")


def test_get_llm_returns_routed_wrapper():
    """Verify get_llm returns a _RoutedLLM wrapper for each agent."""
    from src.utils.llm_router import get_llm
    
    for agent_name in ["planner", "synthesizer", "verifier", "extractor", "validator"]:
        llm = get_llm(agent_name)
        assert hasattr(llm, "invoke"), f"LLM for {agent_name} must have .invoke() method"
        assert hasattr(llm, "_agent_name"), f"LLM for {agent_name} must track agent name"
        assert llm._agent_name == agent_name
        print(f"  ✓ {agent_name} → {llm._provider}/{llm._model}")
    
    print("✅ LLM routing: PASSED")


def test_state_schema():
    """Verify ResearchState includes model_usage_log field."""
    from src.schemas.state import ResearchState
    
    state = ResearchState(query="test query")
    assert hasattr(state, "model_usage_log"), "State must have model_usage_log"
    assert state.model_usage_log == {}, "Default should be empty dict"
    
    print("✅ State schema: PASSED")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("KEEP v2 — Phase 4: Hybrid Cost-Routing Validation")
    print("=" * 60 + "\n")
    
    test_config_loading()
    test_usage_tracker()
    test_tracker_reset()
    test_ollama_check()
    test_get_llm_returns_routed_wrapper()
    test_state_schema()
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60 + "\n")
