from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class Policy:
    tax_rate: float = 0.08          # REDUCED from 0.10
    welfare_amount: float = 8.0      # INCREASED from 5.0
    welfare_threshold: float = 30.0  # INCREASED from 20.0 (catch agents BEFORE starvation)
    public_works_budget: float = 0.0
    law_enforcement: float = 0.3


class Government:
    def __init__(self, world: 'World'):
        self.world = world
        self.treasury = 300.0  # INCREASED starting treasury
        self.policy = Policy()
        self.policy_history: List[Dict] = []
        self.citizens: List[int] = []

        self.starvation_history: List[int] = []
        self.crime_history: List[int] = []
        self.history_window = 10

    def collect_taxes(self):
        alive = [a for a in self.world.agents.values() if a.alive and not a.is_child]
        total_collected = 0.0

        for agent in alive:
            tax = agent.money * self.policy.tax_rate
            agent.money -= tax
            total_collected += tax

        self.treasury += total_collected
        return total_collected

    def distribute_welfare(self) -> List[str]:
        """REDESIGNED: Proactive welfare to prevent starvation, not just react"""
        logs = []
        alive = [a for a in self.world.agents.values() if a.alive and not a.is_child]

        # Tier 1: Critical intervention (food < 15)
        critical = [a for a in alive if a.food < 15]
        for agent in critical:
            if self.treasury >= 10:
                self.treasury -= 10
                agent.money += 10
                agent.food += 5  # DIRECT food aid, not just money
                logs.append(f"CRITICAL AID: Agent {agent.id} received emergency food + $10")

        # Tier 2: Standard welfare (food < threshold)
        needy = [a for a in alive if 15 <= a.food < self.policy.welfare_threshold]
        if needy and self.treasury > 0:
            per_person = min(self.policy.welfare_amount, self.treasury / len(needy))
            for agent in needy:
                if self.treasury >= per_person:
                    self.treasury -= per_person
                    agent.money += per_person
                    logs.append(f"WELFARE: Agent {agent.id} received ${per_person:.1f} (food: {agent.food:.1f})")

        return logs

    def survival_stipend(self) -> List[str]:
        """NEW: Universal survival income for agents with zero money"""
        logs = []
        destitute = [a for a in self.world.agents.values()
                    if a.alive and not a.is_child and a.money < 5 and a.food < 20]

        for agent in destitute:
            if self.treasury >= 5:
                self.treasury -= 5
                agent.money += 5
                logs.append(f"STIPEND: Agent {agent.id} received survival income $5")

        return logs

    def enforce_law(self) -> List[str]:
        logs = []
        for agent in self.world.agents.values():
            if agent.alive and not agent.is_child:
                if self.policy.law_enforcement > 0.5:
                    agent.happiness += 1
        return logs

    def adapt_policy(self):
        alive = [a for a in self.world.agents.values() if a.alive]
        starving = len([a for a in alive if a.food < 20])
        crimes = getattr(self.world, '_crimes_this_step', 0)

        self.starvation_history.append(starving)
        self.crime_history.append(crimes)
        if len(self.starvation_history) > self.history_window:
            self.starvation_history.pop(0)
            self.crime_history.pop(0)

        avg_starvation = sum(self.starvation_history) / len(self.starvation_history) if self.starvation_history else 0
        avg_crimes = sum(self.crime_history) / len(self.crime_history) if self.crime_history else 0

        old_policy = {
            "tax_rate": self.policy.tax_rate,
            "welfare": self.policy.welfare_amount,
            "enforcement": self.policy.law_enforcement,
        }

        # More aggressive adaptation
        if avg_starvation > len(alive) * 0.10:  # LOWERED threshold from 15%
            self.policy.tax_rate = max(0.01, self.policy.tax_rate - 0.03)
            self.policy.welfare_amount += 3.0
            self.policy.welfare_threshold += 5.0
        elif avg_starvation < len(alive) * 0.03:
            self.policy.tax_rate = min(0.25, self.policy.tax_rate + 0.01)
            self.policy.welfare_amount = max(5.0, self.policy.welfare_amount - 1.0)

        if avg_crimes > len(alive) * 0.03:
            self.policy.law_enforcement = min(1.0, self.policy.law_enforcement + 0.1)
            self.policy.tax_rate = min(0.25, self.policy.tax_rate + 0.01)
        elif avg_crimes < len(alive) * 0.005:
            self.policy.law_enforcement = max(0.1, self.policy.law_enforcement - 0.05)

        if old_policy != {
            "tax_rate": self.policy.tax_rate,
            "welfare": self.policy.welfare_amount,
            "enforcement": self.policy.law_enforcement,
        }:
            self.policy_history.append({
                "timestep": self.world.timestep,
                "policy": {
                    "tax_rate": round(self.policy.tax_rate, 2),
                    "welfare_amount": round(self.policy.welfare_amount, 1),
                    "welfare_threshold": round(self.policy.welfare_threshold, 1),
                    "law_enforcement": round(self.policy.law_enforcement, 2),
                },
                "trigger": "starvation_spike" if avg_starvation > len(alive) * 0.10 else "crime_spike" if avg_crimes > len(alive) * 0.03 else "stability",
            })

    def step(self) -> List[str]:
        logs = []
        self.adapt_policy()
        tax_revenue = self.collect_taxes()
        if tax_revenue > 0:
            logs.append(f"GOV: Collected ${tax_revenue:.1f} in taxes (rate: {self.policy.tax_rate:.0%})")
        logs.extend(self.distribute_welfare())
        logs.extend(self.survival_stipend())  # NEW
        logs.extend(self.enforce_law())
        return logs

    def to_dict(self) -> dict:
        return {
            "treasury": round(self.treasury, 1),
            "tax_rate": round(self.policy.tax_rate, 2),
            "welfare_amount": round(self.policy.welfare_amount, 1),
            "welfare_money_threshold": 20.0,
            "welfare_food_threshold": round(self.policy.welfare_threshold, 1),
            "policy_history": self.policy_history[-5:],
        }
