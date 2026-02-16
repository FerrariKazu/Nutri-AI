import asyncio
import logging
from backend.intelligence.claim_enricher import enrich_claim

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_evidence_resolution():
    print("\n--- TEST: Caffeine Evidence (Contradiction) ---")
    caffeine_claim = {
        "id": "caffeine_1",
        "statement": "Caffeine activates TAS2R10 receptors",
        "domain": "biological"
    }
    enriched = enrich_claim(caffeine_claim)
    print(f"Confidence: {enriched['confidence']['current']} ({enriched['confidence']['tier']})")
    print(f"Evidence Records: {len(enriched['evidence'])}")
    print(f"Contradiction Present: {any(e['effect_direction'] == 'contradictory' for e in enriched['evidence'])}")
    
    print("\n--- TEST: Sugar Evidence (Consensus) ---")
    sugar_claim = {
        "id": "sugar_1",
        "statement": "Sucrose binds to TAS1R2",
        "domain": "biological"
    }
    enriched = enrich_claim(sugar_claim)
    print(f"Confidence: {enriched['confidence']['current']} ({enriched['confidence']['tier']})")
    print(f"Evidence Records: {len(enriched['evidence'])}")
    
    print("\n--- TEST: Hard Stop (Unknown Mechanism) ---")
    fake_claim = {
        "id": "fake_1",
        "statement": "Xenomorph blood inhibits steel girders",
        "domain": "biological"
    }
    try:
        enrich_claim(fake_claim)
        print("FAIL: Hard Stop did not trigger for unknown mechanism!")
    except ValueError as e:
        print(f"PASS: Hard Stop triggered as expected: {e}")

if __name__ == "__main__":
    asyncio.run(test_evidence_resolution())
