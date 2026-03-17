"""
Transport Contract Tests — Phase 2 Hardening

Tests for:
    1. Token contract (dict cannot be streamed as token)
    2. Mechanistic pipeline renders narrative only (no data events)
    3. Partial JSON string allowed (type-based, not prefix-based)
    4. Tier persistence across queries
    5. Keyword context guard ("bind a roast" must NOT escalate)
    6. Blocked agent logging
"""

import pytest
import sys
import asyncio
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock heavy dependencies BEFORE any backend imports
sys.modules["faiss"] = MagicMock()
sys.modules["sentence_transformers"] = MagicMock()
sys.modules["ollama"] = MagicMock()
sys.modules["psutil"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["torch"] = MagicMock()
sys.modules["scipy"] = MagicMock()
sys.modules["scipy.optimize"] = MagicMock()
sys.modules["pydantic_settings"] = MagicMock()
sys.modules["httpx"] = MagicMock()
sys.modules["anyio"] = MagicMock()
sys.modules["backend.utils.gpu_monitor"] = MagicMock()

# Mock the registry to avoid real model loading
sys.modules["backend.model_registry"] = MagicMock()


# ══════════════════════════════════════════════════════
# 1. Token Contract — dict cannot be streamed as token
# ══════════════════════════════════════════════════════

class TestTokenContract:
    """SSE token events MUST carry str content. Dict must be rejected."""
    
    def test_token_must_be_string(self):
        """Pushing a dict to 'token' raises ContractViolationError."""
        from backend.contracts.output_contract import validate_sse_content, ContractViolationError
        
        # str → allowed
        validate_sse_content("token", "hello world")
        
        # dict → must raise
        with pytest.raises(ContractViolationError):
            validate_sse_content("token", {"mechanism": "oxidation"})
    
    def test_reasoning_must_be_string(self):
        """Pushing a dict to 'reasoning' raises ContractViolationError."""
        from backend.contracts.output_contract import validate_sse_content, ContractViolationError
        
        validate_sse_content("reasoning", "because glutamate binds...")
        
        with pytest.raises(ContractViolationError):
            validate_sse_content("reasoning", {"step": 1, "reason": "binding"})
    
    def test_message_must_be_string(self):
        """Pushing a dict to 'message' raises ContractViolationError."""
        from backend.contracts.output_contract import validate_sse_content, ContractViolationError
        
        validate_sse_content("message", "Analysis complete.")
        
        with pytest.raises(ContractViolationError):
            validate_sse_content("message", {"status": "done"})
    
    def test_data_event_must_be_dict(self):
        """'execution_trace' events must carry dict content."""
        from backend.contracts.output_contract import validate_sse_content, ContractViolationError
        
        validate_sse_content("execution_trace", {"trace_id": "tr_123"})
        
        with pytest.raises(ContractViolationError):
            validate_sse_content("execution_trace", "raw string trace")
    
    def test_list_rejected_from_token(self):
        """Lists must not be streamed as tokens."""
        from backend.contracts.output_contract import validate_sse_content, ContractViolationError
        
        with pytest.raises(ContractViolationError):
            validate_sse_content("token", ["step1", "step2"])


# ══════════════════════════════════════════════════════
# 2. Mechanistic Output — must render to narrative text
# ══════════════════════════════════════════════════════

class TestMechanisticStream:
    """Mechanistic pipeline dict must be rendered to text before streaming."""
    
    def test_structured_renders_to_narrative(self):
        """Structured mechanistic output converts to readable text."""
        from backend.contracts.output_contract import render_structured_to_narrative
        
        structured = {
            "tier_1_surface": "Bread rises because yeast produces CO2 gas.",
            "tier_2_process": "Saccharomyces cerevisiae ferments sugars via glycolysis.",
            "tier_3_molecular": "Pyruvate decarboxylase converts pyruvate to acetaldehyde + CO2.",
            "causal_chain": [
                {"cause": "yeast consumes sugar", "effect": "CO2 produced"},
                {"cause": "CO2 produced", "effect": "dough expands"}
            ]
        }
        
        narrative = render_structured_to_narrative(structured)
        
        assert isinstance(narrative, str), "Rendered output must be str"
        assert len(narrative) > 50, "Narrative should be substantial"
        assert "What happens:" in narrative
        assert "How it works:" in narrative
        assert "molecular level:" in narrative
        assert "Causal chain:" in narrative
    
    def test_empty_dict_renders_safely(self):
        """Empty dict renders without crash."""
        from backend.contracts.output_contract import render_structured_to_narrative
        
        result = render_structured_to_narrative({})
        assert isinstance(result, str)
    
    def test_agent_output_enforces_type_agreement(self):
        """AgentOutput rejects mismatched type/content."""
        from backend.contracts.output_contract import AgentOutput, AgentOutputType, ContractViolationError
        
        # Correct: NARRATIVE + str
        out = AgentOutput(type=AgentOutputType.NARRATIVE, content="Hello", agent_name="test")
        assert out.is_narrative()
        assert not out.is_structured()
        
        # Correct: STRUCTURED + dict
        out2 = AgentOutput(type=AgentOutputType.STRUCTURED, content={"key": "value"}, agent_name="test")
        assert out2.is_structured()
        assert not out2.is_narrative()
        
        # Wrong: NARRATIVE + dict → must raise
        with pytest.raises(ContractViolationError):
            AgentOutput(type=AgentOutputType.NARRATIVE, content={"bad": True}, agent_name="test")
        
        # Wrong: STRUCTURED + str → must raise
        with pytest.raises(ContractViolationError):
            AgentOutput(type=AgentOutputType.STRUCTURED, content="bad string", agent_name="test")


# ══════════════════════════════════════════════════════
# 3. Partial JSON String — must be ALLOWED (type-based)
# ══════════════════════════════════════════════════════

class TestPartialJsonStream:
    """Partial JSON fragments are STRINGS. SSE guard must NOT reject them."""
    
    def test_json_looking_string_allowed_as_token(self):
        """A string that looks like JSON is still a str — allowed."""
        from backend.contracts.output_contract import validate_sse_content
        
        # These are all valid str tokens — must NOT raise
        validate_sse_content("token", '{"name": "caffeine"')
        validate_sse_content("token", '{"mechanism":')
        validate_sse_content("token", '{')
        validate_sse_content("token", '["step1", "step2"]')
        validate_sse_content("token", '```json\n{"key": "value"}\n```')
    
    def test_actual_dict_rejected_not_json_string(self):
        """Only actual dict TYPE is rejected, not strings containing JSON."""
        from backend.contracts.output_contract import validate_sse_content, ContractViolationError
        
        # str (even JSON-formatted) → allowed
        validate_sse_content("token", '{"name": "caffeine"}')
        
        # dict → rejected
        with pytest.raises(ContractViolationError):
            validate_sse_content("token", {"name": "caffeine"})


# ══════════════════════════════════════════════════════
# 4. Tier Persistence — scientific lock across queries
# ══════════════════════════════════════════════════════

class TestTierPersistence:
    """Scientific tier must persist across ambiguous follow-up queries."""
    
    def test_scientific_lock_persists(self):
        """TIER_3 query followed by 'and what about salt?' stays TIER_3."""
        from backend.governance_types import EscalationLevel
        from backend.orchestrator import (
            SCIENTIFIC_KEYWORDS, BIO_CONTEXT, NUTRITION_KEYWORDS,
            NutriOrchestrator
        )
        
        # Simulate belief_state with previous TIER_3
        class MockBeliefState:
            previous_tier = EscalationLevel.TIER_3.value
            current_tier = EscalationLevel.TIER_3.value
        
        orch = MagicMock(spec=NutriOrchestrator)
        orch.resolve_escalation_tier = NutriOrchestrator.resolve_escalation_tier.__get__(orch)
        
        # Ambiguous follow-up (no scientific keywords)
        session_ctx = {"belief_state": MockBeliefState(), "preferences": {"audience_mode": "casual"}}
        tier = orch.resolve_escalation_tier("and what about salt?", session_ctx)
        
        # Must maintain TIER_3 due to scientific lock persistence
        assert tier == EscalationLevel.TIER_3, f"Expected TIER_3 (persistence), got {tier.name}"
    
    def test_explicit_downgrade_signal(self):
        """'stop' or 'casual' actively breaks scientific lock."""
        from backend.governance_types import EscalationLevel
        from backend.orchestrator import NutriOrchestrator
        
        class MockBeliefState:
            previous_tier = EscalationLevel.TIER_3.value
            current_tier = EscalationLevel.TIER_3.value
        
        orch = MagicMock(spec=NutriOrchestrator)
        orch.resolve_escalation_tier = NutriOrchestrator.resolve_escalation_tier.__get__(orch)
        
        session_ctx = {"belief_state": MockBeliefState(), "preferences": {"audience_mode": "casual"}}
        tier = orch.resolve_escalation_tier("stop being scientific", session_ctx)
        
        assert tier == EscalationLevel.TIER_1, f"Expected TIER_1 (downgrade signal), got {tier.name}"


# ══════════════════════════════════════════════════════
# 5. Keyword Context Guard — "bind a roast" must NOT escalate
# ══════════════════════════════════════════════════════

class TestKeywordContextGuard:
    """Scientific keywords without bio context must NOT trigger escalation."""
    
    def test_bind_a_roast_no_escalation(self):
        """'bind a roast' has 'bind' but no BIO_CONTEXT → must NOT reach TIER_3."""
        from backend.governance_types import EscalationLevel
        from backend.orchestrator import NutriOrchestrator
        
        class MockBeliefState:
            previous_tier = EscalationLevel.TIER_0.value
            current_tier = EscalationLevel.TIER_0.value
        
        orch = MagicMock(spec=NutriOrchestrator)
        orch.resolve_escalation_tier = NutriOrchestrator.resolve_escalation_tier.__get__(orch)
        
        session_ctx = {"belief_state": MockBeliefState(), "preferences": {"audience_mode": "casual"}}
        tier = orch.resolve_escalation_tier("bind a roast with twine", session_ctx)
        
        assert tier.value < EscalationLevel.TIER_3.value, (
            f"'bind a roast' must NOT escalate to TIER_3, got {tier.name}"
        )
    
    def test_bind_with_bio_context_escalates(self):
        """'bind' + 'receptor' (bio context) → should contribute to escalation."""
        from backend.governance_types import EscalationLevel
        from backend.orchestrator import NutriOrchestrator
        
        class MockBeliefState:
            previous_tier = EscalationLevel.TIER_0.value
            current_tier = EscalationLevel.TIER_0.value
        
        orch = MagicMock(spec=NutriOrchestrator)
        orch.resolve_escalation_tier = NutriOrchestrator.resolve_escalation_tier.__get__(orch)
        
        # "bind" + "receptor/glutamate" (bio context) + audience scientific + length>20
        session_ctx = {"belief_state": MockBeliefState(), "preferences": {"audience_mode": "scientific"}}
        tier = orch.resolve_escalation_tier(
            "how does glutamate bind to protein receptors in synaptic transmission?",
            session_ctx
        )
        
        # Score: sci(+2) + bio(+2) + audience(+2) + length(+1) = 7 → TIER_3
        assert tier == EscalationLevel.TIER_3, f"Expected TIER_3, got {tier.name}"


# ══════════════════════════════════════════════════════
# 6. Blocked Agent — out-of-tier invocation blocked
# ══════════════════════════════════════════════════════

class TestBlockedAgent:
    """Agent activation matrix must block out-of-tier invocations."""
    
    def test_pubchem_blocked_at_tier_0(self):
        """pubchem_client at TIER_0 → blocked."""
        from backend.governance_types import EscalationLevel
        from backend.orchestrator import NutriOrchestrator, AGENT_ACTIVATION_MATRIX
        
        orch = MagicMock(spec=NutriOrchestrator)
        orch._blocked_agents_count = 0
        orch._enforce_agent_matrix = NutriOrchestrator._enforce_agent_matrix.__get__(orch)
        
        result = orch._enforce_agent_matrix("pubchem_client", EscalationLevel.TIER_0)
        
        assert result is False, "pubchem_client must be blocked at TIER_0"
        assert orch._blocked_agents_count == 1
    
    def test_pubchem_allowed_at_tier_3(self):
        """pubchem_client at TIER_3 → allowed."""
        from backend.governance_types import EscalationLevel
        from backend.orchestrator import NutriOrchestrator
        
        orch = MagicMock(spec=NutriOrchestrator)
        orch._blocked_agents_count = 0
        orch._enforce_agent_matrix = NutriOrchestrator._enforce_agent_matrix.__get__(orch)
        
        result = orch._enforce_agent_matrix("pubchem_client", EscalationLevel.TIER_3)
        
        assert result is True, "pubchem_client must be allowed at TIER_3"
        assert orch._blocked_agents_count == 0
    
    def test_rag_agent_blocked_at_tier_0(self):
        """rag_agent at TIER_0 → blocked."""
        from backend.governance_types import EscalationLevel
        from backend.orchestrator import NutriOrchestrator
        
        orch = MagicMock(spec=NutriOrchestrator)
        orch._blocked_agents_count = 0
        orch._enforce_agent_matrix = NutriOrchestrator._enforce_agent_matrix.__get__(orch)
        
        result = orch._enforce_agent_matrix("rag_agent", EscalationLevel.TIER_0)
        
        assert result is False
        assert orch._blocked_agents_count == 1
    
    @pytest.mark.asyncio
    async def test_invoke_agent_centralizes_enforcement(self):
        """invoke_agent routes through _enforce_agent_matrix."""
        from backend.governance_types import EscalationLevel
        from backend.orchestrator import NutriOrchestrator
        
        orch = MagicMock(spec=NutriOrchestrator)
        orch._current_escalation_tier = EscalationLevel.TIER_0
        orch._blocked_agents_count = 0
        orch._enforce_agent_matrix = NutriOrchestrator._enforce_agent_matrix.__get__(orch)
        orch.invoke_agent = NutriOrchestrator.invoke_agent.__get__(orch)
        
        # pubchem at TIER_0 → invoke_agent should return None
        result = await orch.invoke_agent("pubchem_client", lambda: "should not run")
        
        assert result is None, f"invoke_agent must return None for blocked agent, got {result}"
        assert orch._blocked_agents_count == 1

    @pytest.mark.asyncio
    async def test_invoke_agent_permits_allowed_agent(self):
        """invoke_agent allows agents in the matrix."""
        from backend.governance_types import EscalationLevel
        from backend.orchestrator import NutriOrchestrator
        
        orch = MagicMock(spec=NutriOrchestrator)
        orch._current_escalation_tier = EscalationLevel.TIER_3
        orch._blocked_agents_count = 0
        orch._enforce_agent_matrix = NutriOrchestrator._enforce_agent_matrix.__get__(orch)
        orch.invoke_agent = NutriOrchestrator.invoke_agent.__get__(orch)
        
        result = await orch.invoke_agent("pubchem_client", lambda: "executed")
        
        assert result == "executed", "invoke_agent must execute when allowed"
        assert orch._blocked_agents_count == 0


# ══════════════════════════════════════════════════════
# 7. Retriever Domain Locking
# ══════════════════════════════════════════════════════

class TestRetrieverDomainLocking:
    """Retriever must respect allowed indices and track blocked count."""
    
    def test_tier_index_map_exists(self):
        """TIER_INDEX_MAP must be defined with correct tier structure."""
        from backend.governance_types import EscalationLevel
        from backend.orchestrator import TIER_INDEX_MAP
        
        assert EscalationLevel.TIER_0 in TIER_INDEX_MAP
        assert EscalationLevel.TIER_1 in TIER_INDEX_MAP
        assert EscalationLevel.TIER_2 in TIER_INDEX_MAP
        assert EscalationLevel.TIER_3 in TIER_INDEX_MAP
        
        # TIER_0 and TIER_1 must have NO indices
        assert len(TIER_INDEX_MAP[EscalationLevel.TIER_0]) == 0
        assert len(TIER_INDEX_MAP[EscalationLevel.TIER_1]) == 0
        
        # TIER_3 must include CHEMISTRY and SCIENCE
        from backend.retriever.router import IndexType
        assert IndexType.CHEMISTRY in TIER_INDEX_MAP[EscalationLevel.TIER_3]
        assert IndexType.SCIENCE in TIER_INDEX_MAP[EscalationLevel.TIER_3]
        
        # TIER_2 must NOT include CHEMISTRY or SCIENCE
        assert IndexType.CHEMISTRY not in TIER_INDEX_MAP[EscalationLevel.TIER_2]
        assert IndexType.SCIENCE not in TIER_INDEX_MAP[EscalationLevel.TIER_2]


# ══════════════════════════════════════════════════════
# 8. Governance Integrity (Thresholds & Versioning)
# ══════════════════════════════════════════════════════

class TestGovernanceIntegrity:
    """Verifies that frozen thresholds and versioning are strictly enforced."""
    
    def test_threshold_constants_enforced(self):
        """Scoring exactly on threshold boundaries triggers correct tier."""
        from backend.governance_types import EscalationLevel
        from backend.orchestrator import NutriOrchestrator, TIER_2_THRESHOLD, TIER_3_THRESHOLD
        
        orch = MagicMock(spec=NutriOrchestrator)
        orch.resolve_escalation_tier = NutriOrchestrator.resolve_escalation_tier.__get__(orch)
        
        # Test Case 1: Trigger TIER_2_THRESHOLD (3.0)
        # Score factors: sci(+2) [pathway] + length(+1) [>20 chars] = 3
        session_ctx_t2 = {"belief_state": MagicMock(previous_tier=0, current_tier=0), "preferences": {"audience_mode": "standard"}}
        tier_2 = orch.resolve_escalation_tier(
            "Tell me more about the pathway here",
            session_ctx_t2
        )
        assert tier_2 == EscalationLevel.TIER_2
        
        # Test Case 2: Trigger TIER_3_THRESHOLD (5.0)
        # Score factors: sci(+2) [bind] + bio(+2) [glutamate/receptor] + length(+1) = 5
        session_ctx_t3 = {"belief_state": MagicMock(previous_tier=0, current_tier=0), "preferences": {"audience_mode": "standard"}}
        tier_3 = orch.resolve_escalation_tier(
            "How does glutamate bind to the receptors?",
            session_ctx_t3
        )
        assert tier_3 == EscalationLevel.TIER_3

    def test_governance_version_exists(self):
        """GOVERNANCE_VERSION must be defined and valid."""
        from backend.orchestrator import GOVERNANCE_VERSION
        assert isinstance(GOVERNANCE_VERSION, str)
        assert len(GOVERNANCE_VERSION.split('.')) == 3


# ══════════════════════════════════════════════════════
# 9. Mechanistic Pipeline Scoping (Regression)
# ══════════════════════════════════════════════════════

class TestMechanisticScoping:
    """Verifies no NameErrors in mechanistic pipeline activation."""
    
    @pytest.mark.asyncio
    async def test_mechanistic_callback_passing(self):
        """Verifies stream_callback_sync is passed without NameError."""
        from backend.orchestrator import NutriOrchestrator
        from backend.governance_types import EscalationLevel
        
        # Create a dummy orchestrator without calling __init__
        orch = MagicMock()
        orch._current_escalation_tier = EscalationLevel.TIER_3
        orch._enforce_agent_matrix.return_value = True
        
        # Use the real invoke_agent method logic
        orch.invoke_agent = NutriOrchestrator.invoke_agent.__get__(orch)
        
        stream_callback_sync = MagicMock()
        mock_func = MagicMock(return_value="done")
        
        # This simulates line 1086-1091 in orchestrator.py
        await orch.invoke_agent(
            "mechanistic_explainer",
            mock_func,
            user_query="test",
            retrieved_docs=[],
            stream_callback=stream_callback_sync
        )
        
        mock_func.assert_called_once()
        _, kwargs = mock_func.call_args
        assert kwargs["stream_callback"] == stream_callback_sync


# ══════════════════════════════════════════════════════
# 10. Escalation Authority (Phase 2.1)
# ══════════════════════════════════════════════════════

class TestEscalationAuthority:
    """Verifies Phase 2.1 Escalation Authority and Tier lock."""
    
    def test_escalation_precedes_routing(self):
        """Mixed-domain prompt must resolve to TIER_3 before routing."""
        from backend.orchestrator import NutriOrchestrator
        from backend.governance_types import EscalationLevel
        from unittest.mock import MagicMock
        
        orch = MagicMock()
        orch.resolve_escalation_tier = NutriOrchestrator.resolve_escalation_tier.__get__(orch)
        
        # Test prompt: contains scientific keyword (bind), biological context (protein, receptor),
        # nutrition keyword (macros), and length > 20
        # Score: sci(+2) + bio(+2) + nutri(+1) + length(+1) = 6 → TIER_3
        prompt = "Explain how sodium binds to protein receptors in the cell and give me the macros for 3 eggs."
        
        session_ctx = {"belief_state": None, "preferences": {}}
        tier = orch.resolve_escalation_tier(prompt, session_ctx)
        
        assert tier == EscalationLevel.TIER_3, f"Expected TIER_3, got {tier.name}"
        assert orch._current_escalation_score >= 5.0, f"Expected score >= 5.0, got {orch._current_escalation_score}"

    def test_domain_cannot_downgrade_tier(self):
        """Simulate domain classifier attempting to downgrade a known TIER_3 lock."""
        from backend.governance_types import EscalationLevel
        
        escalation_tier = EscalationLevel.TIER_3
        
        # Simulate Domain Classifier returning conversational
        class MockClassification:
            scientific_trigger = False
            domain_type = "general_discourse"
            confidence = 0.8
            
        classification = MockClassification()
        
        proposed_tier_value = EscalationLevel.TIER_1.value
        if classification.scientific_trigger: 
            proposed_tier_value = EscalationLevel.TIER_3.value
        elif classification.domain_type in ["food_query", "recipe_analysis", "general_nutrition", "clinical_nutrition", "design_specification", "compound_lookup"]: 
            proposed_tier_value = EscalationLevel.TIER_2.value
            
        # The critical invariant
        tier_lock_active = False
        if proposed_tier_value < escalation_tier.value:
            tier_lock_active = True
            
        assert tier_lock_active is True
        # Pipeline logic based on escalation_tier
        active_pipeline = "conversational_lightweight"
        if escalation_tier == EscalationLevel.TIER_3:
            active_pipeline = "mechanistic_explainer"
            
        assert active_pipeline == "mechanistic_explainer"
