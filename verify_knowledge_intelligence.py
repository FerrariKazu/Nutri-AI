import sys
import os
import math
import logging

# Add backend to path
sys.path.append(os.getcwd())

# Configure logging to see errors
logging.basicConfig(level=logging.INFO)

from backend.intelligence.claim_enricher import enrich_claim
from backend.intelligence.claim_filter import is_mechanistic
from backend.contracts.intelligence_schema import Origin

def test_sucrose_repair():
    print("🧪 Test 1: Sucrose Repair (Normalization, Verification, Depth)")
    # Input with uppercase and extra spaces to test normalization
    claim = {"text": "   SUCROSE   is sweet."}
    enriched = enrich_claim(claim)
    
    # 1. Normalization & Recognition
    assert "sucrose" in enriched.get("compounds", []), "Normalization failed: 'sucrose' not found in compounds"
    
    # 2. Registry Match Guarantee
    assert enriched.get("verified") is True, "Verified flag missing"
    assert enriched.get("verification_level") == "literature-backed", "Verification level incorrect"
    assert enriched.get("decision") == "ACCEPT", "Decision must be ACCEPT"
    
    # 3. Source Attachment
    evidence = enriched.get("evidence", [])
    assert isinstance(evidence, list) and len(evidence) > 0, "Evidence list missing or empty"
    pubchem = next((e for e in evidence if "PubChem" in e["name"]), None)
    assert pubchem, "PubChem evidence missing"
    assert "5988" in pubchem["url"], "PubChem URL incorrect"
    
    # 4. Mechanism Depth Injection (IP3/Ca2+) & Tier 2 Materialization
    # Check for new 'mechanism' object instead of just 'graph'
    mechanism = enriched.get("mechanism", {})
    assert mechanism, "Tier 2 Mechanism object missing!"
    
    nodes = {n["id"]: n for n in mechanism.get("nodes", [])}
    print(f"   - Mechanism nodes: {len(nodes)}")
    
    # Check for IP3/Ca2+ node
    ip3_found = any("ip3_ca" in n_id for n_id in nodes)
    assert ip3_found, "Canonical Pathway Upgrade Failed: IP3/Ca2+ node missing from mechanism"
    
    # Check for Gustducin
    gust_found = any("gustducin" in n_id for n_id in nodes)
    assert gust_found, "Gustducin missing from mechanism"

    # Check Critical Flags
    assert enriched.get("hasTier2") is True, "hasTier2 flag missing or False"
    metrics = enriched.get("metrics", {})
    assert metrics.get("moaCoverage") == 1.0, "metrics.moaCoverage missing or not 1.0"
    
    # 5. Confidence Model
    conf = enriched["confidence"]["current"]
    print(f"   - Confidence: {conf}")
    assert conf > 0.6, "Confidence too low for verified claim"
    assert not math.isnan(conf), "NaN found in confidence"
    
    print("✅ Sucrose Repair Passed")

def test_caffeine_provenance():
    print("🧪 Test 2: Caffeine Provenance (UniProt)")
    claim = {"text": "Caffeine binds to receptors."}
    enriched = enrich_claim(claim)
    
    evidence = enriched.get("evidence", [])
    uniprot = next((e for e in evidence if "UniProt" in e["name"]), None)
    assert uniprot, "UniProt evidence missing"
    assert "Q9NYW0" in uniprot["url"], "UniProt URL incorrect"
    print("✅ Caffeine Provenance Passed")

def test_hard_asserts():
    print("🧪 Test 3: Hard Asserts (Simulated)")
    # We can't easily force a corruption without mocking ontology, 
    # but we can verify that a valid claim DOES NOT raise.
    try:
        enrich_claim({"text": "Sucrose is sweet"})
    except ValueError as e:
        assert False, f"Valid claim raised ValueError: {e}"
        
    print("✅ Hard Asserts Check Passed (Negative Test)")

if __name__ == "__main__":
    try:
        test_sucrose_repair()
        test_caffeine_provenance()
        test_hard_asserts()
        print("\n🏆 ALL REPAIR CONTRACTS VERIFIED!")
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        sys.exit(1)
