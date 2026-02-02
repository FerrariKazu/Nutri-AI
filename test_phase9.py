import sys
import os
sys.path.append(os.getcwd())
from backend.sensory.sensory_types import ParetoFrontierResult, SensoryVariant, SensoryProfile, UserPreferences
from backend.sensory.selector import VariantSelector

# Mock data
v = SensoryVariant(name="Test", recipe="Test", profile=SensoryProfile(), trade_offs="")
frontier = ParetoFrontierResult(variants=[v], objectives={"crispness": "maximize"})
prefs = UserPreferences(eating_style="comfort")

print("Testing Selection...")
selector = VariantSelector()
res = selector.select(frontier, prefs)
print(f"Selection Result: {res.selected_variant.name}")
