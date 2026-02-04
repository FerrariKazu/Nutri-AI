import os
import httpx
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class USDANutrient:
    name: str
    amount: float
    unit: str

class USDAClient:
    """
    USDA FoodData Central API Client.
    Used for general nutrient lookups (fiber, protein, calories).
    """
    
    BASE_URL = "https://api.nal.usda.gov/fdc/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("USDA_API_KEY", "DEMO_KEY")
        self.timeout = 5.0
        self._cache = {} # Simple in-memory cache

    def search_food(self, query: str) -> Optional[int]:
        """
        Searches for a food and returns the FDC ID.
        """
        if query in self._cache:
            return self._cache[query].get("fdcId")
            
        logger.info(f"[USDA] Searching for food: {query}")
        try:
            with httpx.Client(timeout=self.timeout) as client:
                params = {
                    "api_key": self.api_key,
                    "query": query,
                    "pageSize": 1
                }
                response = client.get(f"{self.BASE_URL}/foods/search", params=params)
                response.raise_for_status()
                data = response.json()
                
                if data.get("foods"):
                    fdc_id = data["foods"][0]["fdcId"]
                    self._cache[query] = {"fdcId": fdc_id}
                    return fdc_id
                    
        except Exception as e:
            logger.error(f"[USDA] Search failed for {query}: {e}")
            
        return None

    def get_nutrients(self, fdc_id: int) -> Dict[str, USDANutrient]:
        """
        Retrieves nutrients for a specific FDC ID.
        """
        logger.info(f"[USDA] Fetching nutrients for FDC ID: {fdc_id}")
        try:
            with httpx.Client(timeout=self.timeout) as client:
                params = {"api_key": self.api_key}
                response = client.get(f"{self.BASE_URL}/food/{fdc_id}", params=params)
                response.raise_for_status()
                data = response.json()
                
                nutrients = {}
                for n in data.get("foodNutrients", []):
                    # FDC schema varies, normalize here
                    nutrient_info = n.get("nutrient", {})
                    name = nutrient_info.get("name", "").lower()
                    amount = n.get("amount", 0.0)
                    unit = nutrient_info.get("unitName", "")
                    
                    if name:
                        nutrients[name] = USDANutrient(name=name, amount=amount, unit=unit)
                        
                return nutrients
                
        except Exception as e:
            logger.error(f"[USDA] Nutrient fetch failed for {fdc_id}: {e}")
            
        return {}
