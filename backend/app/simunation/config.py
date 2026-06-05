from pydantic import BaseModel
from typing import Dict, Any

class SimConfigV2(BaseModel):
    # World layout
    map_width: int = 100
    map_height: int = 100
    
    # Demographics
    initial_population: int = 150
    max_population: int = 1500
    
    # Survival thresholds
    food_consumption_per_step: float = 1.0
    energy_depletion_per_step: float = 5.0
    energy_recovery_sleep: float = 30.0
    health_recovery_rate: float = 5.0
    
    # Life cycles
    adulthood_age: int = 18
    max_age: int = 80
    birth_cost_money: float = 50.0
    birth_cost_food: float = 20.0
    
    # Economy & Pricing
    base_prices: Dict[str, float] = {
        "food": 10.0,
        "raw_materials": 5.0,
        "housing": 100.0,
        "medical_service": 20.0,
        "education": 15.0
    }
    
    # Government policy defaults
    default_tax_rate: float = 0.05
    default_welfare_amount: float = 15.0
    default_welfare_money_threshold: float = 15.0
    default_welfare_food_threshold: float = 2.0
    
    # Starvation / Disease danger
    starve_health_damage: float = 15.0
    disease_outbreak_chance: float = 0.02

# Singleton config instance
config = SimConfigV2()
