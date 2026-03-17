"""
Scientific Trace Contract v1.0
Enforces minimum mechanistic depth for scientific traces.
No silent failures. All violations are logged and actionable.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple, Optional
import logging
from backend.response_modes import ResponseMode
from backend.utils.execution_trace import EpistemicStatus

logger = logging.getLogger(__name__)

SCIENTIFIC_MODES = {ResponseMode.DIAGNOSTIC, ResponseMode.NUTRITION_ANALYSIS, ResponseMode.MECHANISTIC}

@dataclass
class ContractViolation:
    rule: str
    severity: str  # "blocking" | "warning"
    detail: str
    remediation: str

@dataclass
class ContractResult:
    passed: bool
    violations: List[ContractViolation] = field(default_factory=list)
    depth_score: float = 0.0  # 0.0-1.0
    
    def to_dict(self):
        return {
            "passed": self.passed,
            "violations": [
                {"rule": v.rule, "severity": v.severity,
                 "detail": v.detail, "remediation": v.remediation}
                for v in self.violations
            ],
            "depth_score": round(self.depth_score, 3)
        }

# ── SSOT INVARIANTS ──
# 1. NEVER introduce new claim IDs during correction.
# 2. NEVER modify mechanistic anchors or depth levels.
# 3. NEVER modify registry alignment hash.
# 4. NEVER modify evidence tiers or source records.
# 5. ONLY prune unsupported claims or annotate failures.

# ──────────────────────────────────────────────────────────────────────────────
# EPISTEMIC ADJUDICATION FREEZE (v1.3)
# ──────────────────────────────────────────────────────────────────────────────
SCHEMA_VERSION_REQUIRED = 1.3

# Logical Constants - Modification requires Schema Version Bump
FREEZE_CONSTANTS = {
    "INTEGRITY_HARD_THRESHOLD": 0.5,     # Below this = Status Downgrade
    "INTEGRITY_SOFT_THRESHOLD": 0.7,     # Below this = Confidence Dampening
    "CONFIDENCE_DAMPENING_FACTOR": 0.85, # Multiplier for soft failure
    "CONTRACT_WEIGHT": 0.6,              # Weight of contract vs surface
    "SURFACE_WEIGHT": 0.4                # Weight of surface vs contract
}

# Authorized Physiological Systems (Ontology-backed depth 1)
AUTHORIZED_SYSTEMS = {
    "endocrine", "metabolic", "cardiovascular", "nervous", "immune", 
    "digestive", "respiratory", "renal", "muscular", "skeletal"
}

def validate_scientific_trace(trace: Any, response_mode: ResponseMode) -> ContractResult:
    """
    Scientific Trace Contract (STC) v1.0.
    
    Validates trace against STC-001 through STC-006.
    Enforces minimum mechanistic depth and registry alignment.
    """
    # 1. Schema Version Check
    trace_version = getattr(trace, "schema_version", 0)
    if trace_version < SCHEMA_VERSION_REQUIRED:
        logger.error(f"[CONTRACT] Version Mismatch: Trace v{trace_version} < Required v{SCHEMA_VERSION_REQUIRED}")
        # We allow it to proceed with a warning for now, but in PRODUCTION this would block.
    violations = []
    
    # Anchor depth mapping
    # 0 = generic/system, 1 = pathway/process/metabolite/physiological_system, 2 = enzyme, 3 = receptor, 4 = molecule
    def get_anchor_depth(anchor: Dict[str, Any]) -> int:
        a_type = anchor.get("type", "").lower()
        a_name = anchor.get("name", "").lower()

        if a_type == "compound": return 4
        if a_type == "receptor": return 3
        if a_type == "enzyme": return 2
        
        # Physiological Systems (Depth 1) - Must be specific
        if a_type in ["physiological_system", "system"]:
            if any(s in a_name for s in AUTHORIZED_SYSTEMS):
                return 1
            return 0 # "Body system" fails
            
        if a_type in ["pathway", "process", "metabolite"]: return 1
        return 0

    # 1. Claims Existence (STC-001)
    has_claims = len(trace.claims) > 0
    if not has_claims:
        if response_mode in SCIENTIFIC_MODES:
            violations.append(ContractViolation(
                rule="STC-001", severity="blocking",
                detail="Zero claims in scientific mode",
                remediation="Generate fallback claim"
            ))
    
    # 2. Mechanistic Anchors (STC-002) - Depth Implementation
    # Requirement: anchor.depth_level >= 1
    mechanistic_count = 0
    fully_backed_count = 0
    
    for c in trace.claims:
        # Check compounds and receptors individually for depth
        anchors = []
        for cmp in c.get("compounds", []):
            anchors.append({"type": "compound", "name": cmp})
        for rec in c.get("receptors", []):
            anchors.append({"type": "receptor", "name": rec})
        
        # Check mechanism_type if it corresponds to a process/pathway
        if c.get("mechanism_type") and c.get("mechanism_type") != "heuristic":
            anchors.append({"type": "pathway", "name": c.get("mechanism_type")})

        # Check for system anchors
        if c.get("system"):
            anchors.append({"type": "physiological_system", "name": c.get("system")})

        max_depth = max([get_anchor_depth(a) for a in anchors]) if anchors else 0
        has_mechanism = c.get("mechanism") is not None
        is_verified = c.get("verified") is True
        
        # STC-002 Requirement: depth >= 1
        if max_depth >= 1:
            mechanistic_count += 1
            
        if max_depth >= 1 and has_mechanism and is_verified:
            fully_backed_count += 1

    if has_claims and mechanistic_count == 0 and response_mode in SCIENTIFIC_MODES:
        violations.append(ContractViolation(
            rule="STC-002", severity="blocking",
            detail="No mechanistic anchors with depth >= 1 found",
            remediation="Ensure claims link to specific pathways, enzymes, or molecules"
        ))

    # 3. Registry Alignment (STC-003)
    if not trace.registry_hash:
        violations.append(ContractViolation(
            rule="STC-003", severity="blocking", # Upgraded to blocking
            detail="Missing registry hash (Adjudication Anchor Missing)",
            remediation="Check SensoryRegistry snapshot"
        ))

    # 4. Confidence Arithmetic (STC-004)
    bd = getattr(trace, "confidence_breakdown", {})
    if not isinstance(bd, dict) or "final_score" not in bd or "baseline_used" not in bd:
        violations.append(ContractViolation(
            rule="STC-004", severity="warning",
            detail="Malformed confidence breakdown",
            remediation="Ensure trace.confidence_breakdown contains final_score and baseline_used"
        ))
    
    # 5. Evidence Backing (STC-005)
    has_evidence = any(c.get("evidence") or c.get("source") for c in trace.claims)
    if has_claims and not has_evidence and response_mode == ResponseMode.DIAGNOSTIC:
        violations.append(ContractViolation(
            rule="STC-005", severity="warning",
            detail="No evidence sources linked",
            remediation="Enable RAG or Policy check"
        ))

    # 6. Epistemic Status Consistency (STC-006)
    status_str = trace.epistemic_status.value if hasattr(trace.epistemic_status, 'value') else str(trace.epistemic_status)
    high_tier_statuses = ["empirical_verified", "convergent_support", "mechanistically_supported"]
    
    if status_str in high_tier_statuses and len(trace.claims) == 0:
        violations.append(ContractViolation(
            rule="STC-006", severity="blocking",
            detail=f"High epistemic status {status_str} with zero claims",
            remediation="Downgrade status to theoretical"
        ))

    # Calculate Depth Score (0.0 - 1.0)
    depth = 0.0
    if len(trace.claims) > 0:
        depth = fully_backed_count / len(trace.claims)

    # 7. Mechanistic v2.0 Strict Validation
    if getattr(trace, "trace_variant", "standard") == "mechanistic":
        # Check for 3-tier structure
        if not getattr(trace, "tier_1_surface", None):
            violations.append(ContractViolation(
                rule="STC-MECH-001", severity="blocking",
                detail="Missing tier_1_surface in mechanistic trace",
                remediation="Ensure MechanisticExplainer populates tier 1"
            ))
        if not getattr(trace, "tier_2_process", None):
            violations.append(ContractViolation(
                rule="STC-MECH-002", severity="blocking",
                detail="Missing tier_2_process in mechanistic trace",
                remediation="Ensure MechanisticExplainer populates tier 2"
            ))
        if not getattr(trace, "tier_3_molecular", None):
            violations.append(ContractViolation(
                rule="STC-MECH-003", severity="blocking",
                detail="Missing tier_3_molecular in mechanistic trace",
                remediation="Ensure MechanisticExplainer populates tier 3"
            ))
        
        # Check for Graph Integrity
        graph = getattr(trace, "graph", {})
        if not graph or not graph.get("nodes") or len(graph.get("nodes", [])) < 3:
            violations.append(ContractViolation(
                rule="STC-MECH-004", severity="blocking",
                detail=f"Mechanistic graph under-populated (nodes={len(graph.get('nodes', []))}, need >= 3)",
                remediation="Ensure causal chain parsing is generating nodes"
            ))
        
        # Check for Causal Chain
        if not getattr(trace, "causality_chain", None):
            violations.append(ContractViolation(
                rule="STC-MECH-005", severity="blocking",
                detail="Missing causality_chain in mechanistic trace",
                remediation="Ensure MechanisticExplainer generates causal_chain"
            ))

    # Final Violation Audit & Loud Logging
    blocking_violations = [v for v in violations if v.severity == "blocking"]
    warning_violations = [v for v in violations if v.severity == "warning"]
    
    for v in blocking_violations:
        logger.error(f"[STC-FAIL] {v.rule}: {v.detail} | Remediation: {v.remediation}")
    for v in warning_violations:
        logger.warning(f"[STC-WARN] {v.rule}: {v.detail}")
    
    passed = len(blocking_violations) == 0

    return ContractResult(
        passed=passed,
        violations=violations,
        depth_score=depth
    )

def compute_epistemic_integrity(contract_result: Any, surface_result: Dict[str, Any], domain_type: str, trace_registry_hash: str = "") -> Dict[str, Any]:
    """
    Composite integrity score that feeds back into trace confidence.
    
    PRECECEDENCE HIERARCHY:
    1. Registry Failure (Hard) -> INSUFFICIENT_EVIDENCE
    2. STC/Integrity failure (Soft) -> Status Upgrade Blocked & Proportional Downgrade (Verified -> Theoretical)
    3. Surface Mismatch -> Theoretical Downgrade / Warning
    """
    # GUARD 1: Contextual traces are exempt
    if domain_type == "contextual":
        return {
            "score": None,
            "contract_depth": None,
            "surface_coverage": None,
            "adjustment": "skipped_contextual_domain"
        }
    
    # ── HIERARCHY 1: Registry Check ──
    if not trace_registry_hash:
        logger.error("[INTEGRITY] Hard Guard Fail: REGISTRY_MISMATCH")
        return {
            "score": 0.0,
            "contract_depth": 0.0,
            "surface_coverage": 0.0,
            "adjustment": "downgrade_hard_insufficient",
            "reason": "REGISTRY_MISMATCH"
        }

    # Extract depth
    if hasattr(contract_result, 'depth_score'):
        depth = contract_result.depth_score
    elif isinstance(contract_result, dict):
        depth = contract_result.get("depth_score", 0.0)
    else:
        depth = 0.0
        
    coverage = surface_result.get("coverage_ratio", 0.0) if surface_result else 0.0
    
    # ── HIERARCHY 2: Integrity Score ──
    w_contract = FREEZE_CONSTANTS["CONTRACT_WEIGHT"]
    w_surface = FREEZE_CONSTANTS["SURFACE_WEIGHT"]
    integrity = (depth * w_contract) + (coverage * w_surface)
    
    adjustment = "none"
    if integrity < FREEZE_CONSTANTS["INTEGRITY_HARD_THRESHOLD"]:
        # Refinement: Soft Downgrade (Proportional)
        adjustment = "downgrade_soft_theoretical"
        logger.warning(f"[INTEGRITY] Soft Downgrade Triggered: integrity={integrity:.3f}")
    elif integrity < FREEZE_CONSTANTS["INTEGRITY_SOFT_THRESHOLD"]:
        adjustment = "reduce_confidence_multiplier"
        logger.info(f"[INTEGRITY] Confidence Dampening Triggered: integrity={integrity:.3f}")
    
    return {
        "score": round(integrity, 3),
        "contract_depth": round(depth, 3),
        "surface_coverage": round(coverage, 3),
        "adjustment": adjustment,
        "dampening_factor": FREEZE_CONSTANTS["CONFIDENCE_DAMPENING_FACTOR"]
    }

