import random
from typing import Dict, List, Any, Optional, Tuple
from simunation.config import config
from simunation.relationships import RelationshipManager

FIRST_NAMES = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Elizabeth", "William", "Linda", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]

class AdvancedAgent:
    def __init__(self, agent_id: int, role: str, x: int, y: int):
        self.id: int = agent_id
        self.name: str = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        self.role: str = role  # "Farmer", "Trader", "Worker", "Doctor", "Builder", "Miner", "Teacher", "Merchant"
        
        # State
        self.age: int = random.randint(18, 50)
        self.money: float = random.uniform(50.0, 200.0)
        self.food: float = random.uniform(5.0, 15.0)
        self.health: float = 100.0
        self.energy: float = 100.0
        self.happiness: float = 75.0
        self.housing_level: str = "Homeless"  # Homeless, Tent, Hut, House, Large House, Villa
        
        # Grid Coordinates
        self.x: int = x
        self.y: int = y
        self.target_x: int = x
        self.target_y: int = y
        
        # Demographics
        self.family_id: Optional[int] = None
        self.partner_id: Optional[int] = None
        self.children_ids: List[int] = []
        self.is_alive: bool = True
        
        # Personality Traits
        self.greed: float = random.uniform(10.0, 90.0)
        self.cooperation: float = random.uniform(10.0, 90.0)
        self.risk_tolerance: float = random.uniform(10.0, 90.0)
        self.intelligence: float = random.uniform(20.0, 80.0)
        self.ambition: float = random.uniform(10.0, 90.0)
        
        # Items / Inventory stocks
        self.inventory: Dict[str, float] = {
            "food": self.food,
            "raw_materials": 0.0,
            "housing": 0.0,
            "medical_service": 0.0,
            "education": 0.0
        }
        
        self.relationships = RelationshipManager()
        self.last_action: str = "Spawned"
        self.starvation_ticks: int = 0

    def get_item_stock(self, item: str) -> float:
        if item == "food":
            return self.food
        return self.inventory.get(item, 0.0)

    def add_item_stock(self, item: str, amount: float):
        if item == "food":
            self.food += amount
        self.inventory[item] = self.inventory.get(item, 0.0) + amount

    def sub_item_stock(self, item: str, amount: float):
        if item == "food":
            self.food = max(0.0, self.food - amount)
        self.inventory[item] = max(0.0, self.inventory.get(item, 0.0) - amount)

    def consume_purchased_item(self, item: str, amount: float):
        """Consume services or housing upgrades instantly upon purchase."""
        if item == "medical_service":
            self.health = min(100.0, self.health + amount * 15.0)
        elif item == "education":
            self.intelligence = min(100.0, self.intelligence + amount * 3.0)
        elif item == "housing":
            # Upgrade housing level
            levels = ["Homeless", "Tent", "Hut", "House", "Large House", "Villa"]
            curr_idx = levels.index(self.housing_level)
            if curr_idx < len(levels) - 1:
                self.housing_level = levels[curr_idx + 1]

    def consume_resources(self) -> Tuple[bool, str]:
        """Runs every timestep to apply hunger, fatigue, aging."""
        if not self.is_alive:
            return False, "Dead"

        # Age
        if random.random() < 0.05:  # Age slowly
            self.age += 1
            if self.age > config.max_age or (self.age > 65 and random.random() < 0.05):
                self.is_alive = False
                return True, "Died of old age"

        # Food consumption
        if self.food >= config.food_consumption_per_step:
            self.food -= config.food_consumption_per_step
            self.inventory["food"] = self.food
            self.starvation_ticks = 0
        else:
            self.food = 0.0
            self.inventory["food"] = 0.0
            self.starvation_ticks += 1
            self.health = max(0.0, self.health - config.starve_health_damage)
            self.happiness = max(0.0, self.happiness - 20.0)
            if self.health <= 0:
                self.is_alive = False
                return True, "Starved to death"

        # Fatigue
        self.energy = max(0.0, self.energy - config.energy_depletion_per_step)
        if self.energy < 20.0:
            self.energy = min(100.0, self.energy + config.energy_recovery_sleep)
            self.last_action = "Sleeping"
            return False, "Sleeping"

        # Health recovery naturally if fed
        if self.food > 2.0 and self.health < 100.0:
            self.health = min(100.0, self.health + config.health_recovery_rate)

        # Update happiness dynamically
        self.update_happiness()
        
        return False, "Active"

    def update_happiness(self):
        """Happiness score computation based on resources, housing, and social status."""
        food_factor = min(1.0, self.food / 5.0) * 30
        wealth_factor = min(1.0, self.money / 300.0) * 20
        health_factor = (self.health / 100.0) * 30
        
        house_ranks = {"Homeless": 0, "Tent": 10, "Hut": 20, "House": 30, "Large House": 40, "Villa": 50}
        house_factor = house_ranks.get(self.housing_level, 0) / 50 * 20
        
        self.happiness = round(food_factor + wealth_factor + health_factor + house_factor, 2)

    def move_towards_target(self):
        """Move 1 grid step towards target coordinates."""
        if self.x < self.target_x:
            self.x += 1
        elif self.x > self.target_x:
            self.x -= 1

        if self.y < self.target_y:
            self.y += 1
        elif self.y > self.target_y:
            self.y -= 1

    def make_decisions(self, market_prices: Dict[str, float], step: int) -> Tuple[List[Any], Optional[Dict[str, Any]]]:
        """Decide next moves, trade orders, and social actions (crime, family)."""
        orders = []
        crime_event = None

        if not self.is_alive or "Sleeping" in self.last_action:
            return orders, crime_event

        # 1. EMERGENCE OF CRIME: Steal from other agents if desperate
        # Probability based on hunger, low money, high greed, and low happiness
        if self.food < 2.0 and self.money < 15.0 and self.happiness < 40.0:
            crime_prob = (self.greed / 100.0) * 0.4
            if random.random() < crime_prob:
                crime_event = {
                    "type": "theft",
                    "thief_id": self.id,
                    "thief_name": self.name,
                    "target_x": self.x,
                    "target_y": self.y
                }
                self.last_action = "Committed theft"
                return orders, crime_event

        # 2. Production work depending on profession
        if self.role == "Farmer":
            # Need to produce food
            self.add_item_stock("food", 1.8 * (1.0 + self.intelligence/200.0))
            self.last_action = "Harvested food crops"
        elif self.role == "Miner":
            self.add_item_stock("raw_materials", 3.0)
            self.last_action = "Mined ore and raw materials"
        elif self.role == "Builder":
            self.add_item_stock("housing", 0.5)
            self.last_action = "Worked on construction"
        elif self.role == "Doctor":
            self.add_item_stock("medical_service", 1.0)
            self.last_action = "Provided medical care"
        elif self.role == "Teacher":
            self.add_item_stock("education", 1.0)
            self.last_action = "Taught community class"
        elif self.role == "Worker":
            # Earns external salary
            self.money += 12.0
            self.last_action = "Earned industrial labor wage"

        # 3. Formulate Trading Orders
        # Sells excess inventory
        for item, stock in self.inventory.items():
            if item == "food":
                buffer = 5.0 if self.starvation_ticks == 0 else 10.0
                if self.food > buffer:
                    sell_amt = self.food - buffer
                    price = market_prices["food"] * (1.0 + (self.greed - 50.0)/200.0)
                    orders.append({
                        "agent_id": self.id, "type": "sell", "item": "food",
                        "amount": round(sell_amt, 2), "price": round(price, 2)
                    })
            elif item in ["raw_materials", "housing", "medical_service", "education"] and stock > 0.1:
                price = market_prices[item] * (1.0 + (self.greed - 50.0)/200.0)
                orders.append({
                    "agent_id": self.id, "type": "sell", "item": item,
                    "amount": round(stock, 2), "price": round(price, 2)
                })

        # Buy items they are missing
        if self.food < 4.0 and self.money > 5.0:
            buy_amt = 4.0 - self.food
            price = market_prices["food"] * (1.1 if self.starvation_ticks > 0 else 1.0)
            orders.append({
                "agent_id": self.id, "type": "buy", "item": "food",
                "amount": round(buy_amt, 2), "price": round(price, 2)
            })

        # Upgrade housing if wealthy
        if self.money > 120.0 and self.housing_level != "Villa":
            orders.append({
                "agent_id": self.id, "type": "buy", "item": "housing",
                "amount": 1.0, "price": round(market_prices["housing"], 2)
            })

        # Seek doctor if sick
        if self.health < 60.0 and self.money > 20.0:
            orders.append({
                "agent_id": self.id, "type": "buy", "item": "medical_service",
                "amount": 1.0, "price": round(market_prices["medical_service"], 2)
            })

        # Seek education if they want to grow intelligence
        if self.intelligence < 80.0 and self.money > 40.0:
            orders.append({
                "agent_id": self.id, "type": "buy", "item": "education",
                "amount": 1.0, "price": round(market_prices["education"], 2)
            })

        return orders, crime_event
