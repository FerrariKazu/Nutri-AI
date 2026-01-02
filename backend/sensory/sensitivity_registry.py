"""
Nutri Phase 11: Sensory Sensitivity Registry
Static mapping of input parameters to sensory effects based on food science.
"""

# Registry mapping: parameter -> {sensory_dimension: sensitivity_coefficient}
# Coefficient represents the direction and relative strength (0-1) of the effect per unit change.
SENSITIVITY_REGISTRY = {
    "salt_pct": {
        "saltiness": 1.0,
        "umami": 0.6,
        "sweetness": -0.2,
        "bitterness": -0.4
    },
    "surface_moisture": {
        "surface_crust": -0.8,
        "crispness": -0.7,
        "tenderness": 0.3,
        "moistness": 0.4
    },
    "heat_intensity": {
        "surface_crust": 0.9,
        "crispness": 0.8,
        "tenderness": -0.5,
        "chewiness": 0.4,
        "umami": 0.5 # Maillard acceleration
    },
    "sear_duration_min": {
        "surface_crust": 0.7,
        "crispness": 0.6,
        "tenderness": -0.3,
        "umami": 0.4
    },
    "fat_pct": {
        "richness": 1.0,
        "coating": 0.8,
        "tenderness": 0.5,
        "moistness": 0.4
    },
    "sugar_pct": {
        "sweetness": 1.0,
        "surface_crust": 0.4,
        "bitterness": -0.3
    },
    "acid_pct": {
        "tenderness": 0.4,
        "bitterness": -0.2,
        "astringency": 0.3
    },
    "rest_time_min": {
        "moistness": 0.6,
        "tenderness": 0.5,
        "chewiness": -0.4
    }
}

# Documentation for mechanisms mapping parameters to effects
MECHANISM_MAP = {
    "salt_pct": "Sodium ions directly stimulate gustatory receptors and enhance perceived umami while suppressing bitterness via competitive inhibition.",
    "surface_moisture": "Evaporative cooling and latent heat of vaporization inhibit surface temperature rise, delaying Maillard reactions and crust formation.",
    "heat_intensity": "Thermal energy increases the rate of Maillard reactions and moisture loss, but excessive heat accelerates protein coagulation and fiber shortening.",
    "sear_duration_min": "Time-integrated thermal exposure drives the depth of the Maillard layer and the extent of myofibrillar protein denaturation.",
    "fat_pct": "Lipids provide lubrication (richness) and coat the palate, mitigating perception of astringency and tensity.",
    "sugar_pct": "Sucrose concentration directly increases sweetness and provides substrate for caramelization and Maillard complexes.",
    "acid_pct": "Proton concentration affects protein net charge, increasing water-holding capacity at specific pH levels and balancing flavor profiles.",
    "rest_time_min": "Thermal equilibrium and muscle fiber relaxation allow for redistribution of moisture, decreasing perceive toughness."
}
