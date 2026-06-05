import random
from typing import Dict, List, Any
from simunation.config import config
from simunation.agent import Agent

class WorldEngine:
    def __init__(self):
        self.timestep: int = 0
        self.agents: Dict[int, Agent] = {}
        self.tax_pool: float = 0.0
        self.history: List[Dict[str, Any]] = []
        
        # Initialize population
        self._initialize_population()
        
    def _initialize_population(self):
        """Create initial agents based on config ratios and randomized personalities."""
        roles_pool = []
        num_farmers = int(config.population_size * config.farmer_ratio)
        num_laborers = int(config.population_size * config.laborer_ratio)
        num_merchants = config.population_size - num_farmers - num_laborers
        
        roles_pool.extend(["Farmer"] * num_farmers)
        roles_pool.extend(["Laborer"] * num_laborers)
        roles_pool.extend(["Merchant"] * num_merchants)
        random.shuffle(roles_pool)
        
        personalities = ["cooperative", "selfish", "risk-taking"]
        
        for idx, role in enumerate(roles_pool):
            personality = random.choice(personalities)
            agent = Agent(agent_id=idx + 1, role=role, personality=personality)
            self.agents[agent.id] = agent

    def collect_taxes(self) -> float:
        """Collects taxes from all living agents based on their money supply."""
        collected = 0.0
        for agent in self.agents.values():
            if agent.is_alive and agent.money > 0:
                tax = agent.money * config.tax_rate
                agent.money -= tax
                collected += tax
        self.tax_pool += collected
        return round(collected, 2)

    def distribute_welfare(self) -> float:
        """Distribute accumulated tax pool to agents facing starvation or extreme poverty."""
        candidates = []
        for agent in self.agents.values():
            if agent.is_alive:
                if agent.food <= config.welfare_threshold_food or agent.money <= config.welfare_threshold_money:
                    candidates.append(agent)
                    
        if not candidates or self.tax_pool <= 0.0:
            return 0.0
            
        payout = self.tax_pool / len(candidates)
        for agent in candidates:
            agent.money += payout
            agent.last_action += f" (Received ${payout:.1f} welfare)"
            
        distributed = self.tax_pool
        self.tax_pool = 0.0
        return round(distributed, 2)

    def calculate_gini(self) -> float:
        """Calculate Gini coefficient for wealth (money) distribution among living agents."""
        money_vals = sorted([a.money for a in self.agents.values() if a.is_alive])
        n = len(money_vals)
        if n <= 1 or sum(money_vals) == 0:
            return 0.0
        
        sum_money = sum(money_vals)
        index_sum = sum((i + 1) * val for i, val in enumerate(money_vals))
        gini = (2 * index_sum) / (n * sum_money) - (n + 1) / n
        return round(gini, 3)

    def get_stats(self, average_price: float) -> Dict[str, Any]:
        """Compile global stats for the current timestep."""
        living_agents = [a for a in self.agents.values() if a.is_alive]
        total_money = sum(a.money for a in living_agents) + self.tax_pool
        total_food = sum(a.food for a in living_agents)
        
        role_counts = {"Farmer": 0, "Laborer": 0, "Merchant": 0}
        starving_count = 0
        dead_count = sum(1 for a in self.agents.values() if not a.is_alive)
        
        for a in living_agents:
            role_counts[a.role] += 1
            if a.starvation_steps > 0:
                starving_count += 1
                
        gini = self.calculate_gini()
        
        return {
            "timestep": self.timestep,
            "population_alive": len(living_agents),
            "population_starving": starving_count,
            "population_dead": dead_count,
            "roles": role_counts,
            "total_money": round(total_money, 2),
            "total_food": round(total_food, 2),
            "tax_pool": round(self.tax_pool, 2),
            "gini_coefficient": gini,
            "average_food_price": average_price
        }

    def record_history(self, stats: Dict[str, Any]):
        self.history.append(stats)
        if len(self.history) > 200:
            self.history.pop(0)
