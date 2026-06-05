from typing import Dict, Any, List
from simunation.config import config

class Government:
    def __init__(self):
        self.treasury: float = 1000.0
        self.food_reserve: float = 100.0
        self.tax_rate: float = config.default_tax_rate
        self.welfare_amount: float = config.default_welfare_amount
        self.welfare_money_threshold: float = config.default_welfare_money_threshold
        self.welfare_food_threshold: float = config.default_welfare_food_threshold
        self.total_tax_collected_history: List[float] = []
        self.total_welfare_spent_history: List[float] = []

    def run_fiscal_cycle(self, agents_dict: Dict[int, Any], step: int) -> List[str]:
        """Collects taxes from all living agents based on their money supply."""
        logs = []
        # 1. Collect Taxes
        tax_collected = 0.0
        for agent in agents_dict.values():
            if agent.is_alive and agent.money > 0:
                tax = agent.money * self.tax_rate
                agent.money -= tax
                tax_collected += tax
        self.treasury += tax_collected
        self.total_tax_collected_history.append(tax_collected)

        # 2. Distribute Welfare & Food Aid
        welfare_spent = 0.0
        starving_count = 0
        living_count = 0
        
        for agent in agents_dict.values():
            if agent.is_alive:
                living_count += 1
                if agent.starvation_ticks > 0:
                    starving_count += 1
                
                # Check welfare eligibility
                if agent.money < self.welfare_money_threshold or agent.food < self.welfare_food_threshold:
                    payout = min(self.welfare_amount, self.treasury)
                    if payout > 0.1:
                        agent.money += payout
                        self.treasury -= payout
                        welfare_spent += payout
                        agent.last_action += f" (Govt welfare payout ${payout:.1f})"

        self.total_welfare_spent_history.append(welfare_spent)

        # Limit history
        if len(self.total_tax_collected_history) > 100:
            self.total_tax_collected_history.pop(0)
            self.total_welfare_spent_history.pop(0)

        # 3. Dynamic Policy Adjustments based on society state
        starvation_rate = starving_count / living_count if living_count > 0 else 0
        
        policy_changed = False
        if starvation_rate > 0.15:
            # Crisis: lower taxes, boost welfare
            self.tax_rate = max(0.01, self.tax_rate - 0.01)
            self.welfare_amount = min(40.0, self.welfare_amount + 2.0)
            logs.append(f"🏛️ Govt: Starvation crisis ({starvation_rate*100:.1f}%). Tax rate reduced to {self.tax_rate*100:.0f}%, welfare bumped to ${self.welfare_amount:.1f}.")
            policy_changed = True
        elif starvation_rate < 0.05 and self.treasury < 300.0:
            # Tight budget, stable society: raise taxes slightly to avoid bankruptcy
            self.tax_rate = min(0.15, self.tax_rate + 0.01)
            logs.append(f"🏛️ Govt: Treasury low. Tax rate adjusted to {self.tax_rate*100:.0f}%.")
            policy_changed = True

        if not policy_changed and step % 10 == 0:
            logs.append(f"🏛️ Govt: Tax Revenue: ${tax_collected:.1f} | Welfare Spending: ${welfare_spent:.1f} | Treasury: ${self.treasury:.1f}")

        return logs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "treasury": round(self.treasury, 2),
            "food_reserve": round(self.food_reserve, 2),
            "tax_rate": round(self.tax_rate, 3),
            "welfare_amount": round(self.welfare_amount, 2),
            "welfare_money_threshold": round(self.welfare_money_threshold, 2),
            "welfare_food_threshold": round(self.welfare_food_threshold, 2)
        }
