# Nutri-AI Governance Strategy & Risk Management

**Policy Version:** `1.0.0`  
**Schema Status:** Hardened

## 🛡️ Escalation Scoring (Phase 2 Hardening)

The escalation resolver uses a weighted scoring system anchored to fixed code constants.

### Threshold Logic (SSOT)
| Tier | Score Range | Code Constant | Capability |
| :--- | :--- | :--- | :--- |
| **TIER_0** | 0 | - | Pure chat. No retrieval. |
| **TIER_1** | 1-2 | - | Clarification. Single-agent synthesis. |
| **TIER_2** | 3-4 | `TIER_2_THRESHOLD` | Nutrition Research. USDA access. |
| **TIER_3** | 5+ | `TIER_3_THRESHOLD` | Scientific/Molecular. Chemistry access. |

> [!WARNING]
> **Scoring Drift**: Monitor keywords. If casual queries hit Score 3+, increase thresholds.

## 🔒 Scientific Lock Protocol

Maintains TIER_3 context during multi-turn research sessions.

### Edge Case A: Explicit Downshift
- **Input**: "Explain it simply" or "Make it shorter".
- **Behavior**: Maintain `TIER_3` research level but adjust synthesis verbosity.
- **Breaking Signal**: Only "stop", "casual", or "shut up" resets to `TIER_1`.

### Edge Case B: Topic Switch
- **Input**: User shifts from Biochemistry ("glutamate binding") to General Cooking ("how to fry eggs").
- **Behavior**: The Scientific Lock is **broken on domain shift**. If the query hits 0 scientific keywords and high general nutrition score, re-evaluate from `TIER_0`.

## 🏗️ Orchestration Invariants

- **Invoke Gate**: `invoke_agent` is a < 30 line policy-only method. Business logic is forbidden here.
- **Transport**: SSE tokens MUST be `str`. Mechanistic JSON rendered to text via `render_structured_to_narrative`.

## 📈 Lifecycle & Versioning

Any change to escalation logic, keywords, or agent mappings requires:
1. **Version Increment**: Increment `GOVERNANCE_VERSION` in `orchestrator.py`.
2. **Threshold Audit**: Re-verify common casual queries against the new scoring.
3. **Test Update**: Update `test_transport_contracts.py` to cover the new logic.
4. **Changelog**: Record change rationale in this section.
