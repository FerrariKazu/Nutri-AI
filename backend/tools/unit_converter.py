"""
Unit conversion tool for cooking measurements.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Conversion factors to base units
CONVERSIONS = {
    # Weight (to grams)
    "g": 1.0,
    "gram": 1.0,
    "grams": 1.0,
    "kg": 1000.0,
    "kilogram": 1000.0,
    "kilograms": 1000.0,
    "mg": 0.001,
    "milligram": 0.001,
    "milligrams": 0.001,
    "oz": 28.3495,
    "ounce": 28.3495,
    "ounces": 28.3495,
    "lb": 453.592,
    "pound": 453.592,
    "pounds": 453.592,
    
    # Volume (to milliliters)
    "ml": 1.0,
    "milliliter": 1.0,
    "milliliters": 1.0,
    "l": 1000.0,
    "liter": 1000.0,
    "liters": 1000.0,
    "cup": 236.588,
    "cups": 236.588,
    "tbsp": 14.7868,
    "tablespoon": 14.7868,
    "tablespoons": 14.7868,
    "tsp": 4.92892,
    "teaspoon": 4.92892,
    "teaspoons": 4.92892,
    "fl oz": 29.5735,
    "fluid ounce": 29.5735,
    
    # Temperature (to Celsius)
    "c": 1.0,
    "celsius": 1.0,
    "f": "fahrenheit",
    "fahrenheit": "fahrenheit",
}


def convert_units(amount: float, from_unit: str, to_unit: str) -> Optional[float]:
    """
    Convert between cooking units.
    
    Args:
        amount: Amount to convert
        from_unit: Source unit (e.g., "mg", "cup", "f")
        to_unit: Target unit (e.g., "g", "ml", "c")
        
    Returns:
        Converted amount or None if conversion not possible
    """
    try:
        from_unit = from_unit.lower().strip()
        to_unit = to_unit.lower().strip()
        
        # Handle temperature separately
        if from_unit in ["f", "fahrenheit"] and to_unit in ["c", "celsius"]:
            return (amount - 32) * 5/9
        elif from_unit in ["c", "celsius"] and to_unit in ["f", "fahrenheit"]:
            return (amount * 9/5) + 32
        
        # Get conversion factors
        from_factor = CONVERSIONS.get(from_unit)
        to_factor = CONVERSIONS.get(to_unit)
        
        if from_factor is None or to_factor is None:
            logger.warning(f"Unknown unit: {from_unit} or {to_unit}")
            return None
        
        if isinstance(from_factor, str) or isinstance(to_factor, str):
            logger.warning(f"Cannot convert between different unit types")
            return None
        
        # Convert to base unit, then to target unit
        base_amount = amount * from_factor
        result = base_amount / to_factor
        
        logger.info(f"Converted {amount} {from_unit} to {result:.2f} {to_unit}")
        return round(result, 2)
        
    except Exception as e:
        logger.error(f"Error converting units: {e}")
        return None
