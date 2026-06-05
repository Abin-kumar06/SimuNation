import random
from typing import List, Dict, Any, Optional
from simunation.config import config

class Agent:
    def __init__(self, agent_id: int, role: str, personality: str):
        self.id: int = agent_id
        self.role: str = role
        self.personality: str = personality  # "cooperative", "selfish", "risk-taking"
        
        # Initialize resources based on role
        if role == "Farmer":
            self.money: float = config.initial_farmer_money
            self.food: float = config.initial_farmer_food
        elif role == "Laborer":
            self.money: float = config.initial_laborer_money
            self.food: float = config.initial_laborer_food
        elif role == "Merchant":
            self.money: float = config.initial_merchant_money
            self.food: float = config.initial_merchant_food
        else:
            self.money: float = 50.0
            self.food: float = 5.0
            
        self.starvation_steps: int = 0
        self.is_alive: bool = True
        self.memory: List[Dict[str, Any]] = []
        self.last_action: str = "Initialized"
        
        # Track historical successful trade prices to estimate market value
        self.perceived_value: float = config.base_food_price
        
    def consume_food(self) -> str:
        """Consume food for the timestep. Update starvation status."""
        if not self.is_alive:
            return "Dead"
            
        if self.food >= config.food_consumption_per_step:
            self.food -= config.food_consumption_per_step
            self.starvation_steps = 0
            return "Consumed"
        else:
            # Consume remaining food, if any
            self.food = 0.0
            self.starvation_steps += 1
            if self.starvation_steps >= config.max_starvation_steps:
                self.is_alive = False
                self.last_action = "Died of starvation"
                return "Died"
            return "Starving"

    def produce(self) -> Dict[str, float]:
        """Perform role production/work."""
        if not self.is_alive:
            return {}
            
        produced = {}
        if self.role == "Farmer":
            # Produce food
            prod_amount = config.farmer_food_production_per_step
            # If cooperative, occasionally produces a tiny bit more due to community spirit
            if self.personality == "cooperative" and random.random() < 0.2:
                prod_amount += 0.2
            self.food += prod_amount
            produced["food"] = prod_amount
            self.last_action = f"Produced {prod_amount:.1f} food"
        elif self.role == "Laborer":
            # Earn money
            wage = config.laborer_wage_per_step
            self.money += wage
            produced["money"] = wage
            self.last_action = f"Earned ${wage:.1f} wage"
        elif self.role == "Merchant":
            # Merchants produce nothing directly, they earn through trade arbitrage
            self.last_action = "Looking for trade opportunities"
            
        return produced

    def record_trade(self, role: str, amount: float, price_per_unit: float, successful: bool):
        """Record trade in memory and update perceived asset value."""
        self.memory.append({
            "role": role,  # "buyer" or "seller"
            "amount": amount,
            "price": price_per_unit,
            "successful": successful
        })
        # Keep memory size reasonable
        if len(self.memory) > 20:
            self.memory.pop(0)
            
        if successful:
            # Update perceived value via exponential moving average
            alpha = 0.3
            self.perceived_value = (1 - alpha) * self.perceived_value + alpha * price_per_unit

    def make_decisions(self, average_market_price: float) -> List[Dict[str, Any]]:
        """
        Decide on actions/orders based on role, resources, and personality.
        Returns list of order dicts: [{"type": "buy"|"sell", "item": "food", "amount": float, "price": float}]
        """
        if not self.is_alive:
            return []
            
        orders = []
        
        # Base pricing adjusted by personality
        price_modifier = 1.0
        if self.personality == "selfish":
            price_modifier = 1.15  # Sells higher, buys lower
        elif self.personality == "risk-taking":
            price_modifier = 1.25 if random.random() > 0.5 else 0.85  # Volatile pricing
        
        # Estimate fair price using a combination of average market price and personal perceived value
        est_price = (average_market_price + self.perceived_value) / 2.0
        est_price = max(config.min_food_price, min(config.max_food_price, est_price))

        if self.role == "Farmer":
            # Farmers produce food, want to sell excess food above their safety buffer
            safety_buffer = 4.0
            if self.starvation_steps > 0:
                safety_buffer = 8.0  # Panic buffer
                
            if self.food > safety_buffer:
                sell_amount = self.food - safety_buffer
                # Set price based on personality and supply
                price = est_price * price_modifier
                # If they have lots of food, they lower price to dump inventory
                if self.food > 15.0:
                    price *= 0.9
                price = max(config.min_food_price, min(config.max_food_price, price))
                orders.append({
                    "agent_id": self.id,
                    "type": "sell",
                    "item": "food",
                    "amount": round(sell_amount, 2),
                    "price": round(price, 2)
                })

        elif self.role == "Laborer":
            # Laborers consume food, want to buy food if they fall below safety threshold
            safety_threshold = 5.0
            if self.food < safety_threshold:
                # Target getting back to threshold + extra if they have money
                target_buy = safety_threshold - self.food
                if self.money > 150.0:
                    target_buy += 2.0
                
                # Check if they can afford it
                price = est_price
                if self.personality == "selfish":
                    price *= 0.9  # Try to underbid
                
                # Starvation panic: bid higher to guarantee food
                if self.starvation_steps > 0:
                    price *= (1.2 + 0.2 * self.starvation_steps)
                    
                price = max(config.min_food_price, min(config.max_food_price, price))
                
                # Cap purchase by money
                max_affordable = self.money / price if price > 0 else 0
                buy_amount = min(target_buy, max_affordable)
                
                if buy_amount > 0.1:
                    orders.append({
                        "agent_id": self.id,
                        "type": "buy",
                        "item": "food",
                        "amount": round(buy_amount, 2),
                        "price": round(price, 2)
                    })

        elif self.role == "Merchant":
            # Merchants buy low, sell high
            # Define target inventory
            target_inventory = 12.0
            
            # If inventory is low, buy food
            if self.food < target_inventory and self.money > 20.0:
                # Buy if price is attractive (below or near estimated market price)
                buy_price = est_price * 0.9
                if self.personality == "risk-taking":
                    buy_price = est_price * 0.95
                
                buy_price = max(config.min_food_price, min(config.max_food_price, buy_price))
                buy_amount = min(target_inventory - self.food, self.money / buy_price)
                if buy_amount > 0.1:
                    orders.append({
                        "agent_id": self.id,
                        "type": "buy",
                        "item": "food",
                        "amount": round(buy_amount, 2),
                        "price": round(buy_price, 2)
                    })
            
            # If they have inventory, sell at a markup
            if self.food > 2.0:
                sell_amount = self.food - 1.0  # Keep small buffer
                sell_price = est_price * 1.15  # Standard markup
                if self.personality == "selfish":
                    sell_price = est_price * 1.25  # Greedy markup
                elif self.personality == "risk-taking":
                    sell_price = est_price * 1.35  # High risk markup
                
                sell_price = max(config.min_food_price, min(config.max_food_price, sell_price))
                orders.append({
                    "agent_id": self.id,
                    "type": "sell",
                    "item": "food",
                    "amount": round(sell_amount, 2),
                    "price": round(sell_price, 2)
                })

        return orders
