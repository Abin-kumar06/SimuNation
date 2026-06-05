from pydantic import BaseModel

class SimConfig(BaseModel):
    # World settings
    population_size: int = 60
    initial_money_supply: float = 6000.0  # Distributed among agents
    tax_rate: float = 0.05  # 5% tax on money balance each timestep
    welfare_threshold_money: float = 10.0  # Welfare triggers if money is below this
    welfare_threshold_food: float = 2.0    # Welfare triggers if food is below this

    # Role distribution percentages (must sum to 1.0)
    farmer_ratio: float = 0.4
    laborer_ratio: float = 0.5
    merchant_ratio: float = 0.1

    # Production and Consumption
    food_consumption_per_step: float = 1.0
    farmer_food_production_per_step: float = 2.5
    laborer_wage_per_step: float = 15.0  # Laborers earn money working in external economy

    # Starvation settings
    max_starvation_steps: int = 5

    # Pricing & Economic defaults
    base_food_price: float = 10.0
    min_food_price: float = 2.0
    max_food_price: float = 50.0

    # Agent initialization ranges
    initial_farmer_money: float = 50.0
    initial_farmer_food: float = 15.0
    
    initial_laborer_money: float = 100.0
    initial_laborer_food: float = 5.0
    
    initial_merchant_money: float = 300.0
    initial_merchant_food: float = 10.0

# Create a default instance
config = SimConfig()
