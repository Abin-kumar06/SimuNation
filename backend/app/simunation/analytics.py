from typing import List, Dict, Any
from simunation.agent import AdvancedAgent

class AnalyticsManager:
    @staticmethod
    def calculate_gini(agents: List[AdvancedAgent]) -> float:
        money_vals = sorted([a.money for a in agents if a.is_alive])
        n = len(money_vals)
        if n <= 1 or sum(money_vals) == 0:
            return 0.0
        
        sum_money = sum(money_vals)
        index_sum = sum((i + 1) * val for i, val in enumerate(money_vals))
        gini = (2 * index_sum) / (n * sum_money) - (n + 1) / n
        return round(gini, 3)

    @staticmethod
    def get_age_distribution(agents: List[AdvancedAgent]) -> Dict[str, int]:
        bins = {"0-17": 0, "18-35": 0, "36-50": 0, "51-65": 0, "66+": 0}
        for a in agents:
            if not a.is_alive:
                continue
            if a.age < 18:
                bins["0-17"] += 1
            elif a.age <= 35:
                bins["18-35"] += 1
            elif a.age <= 50:
                bins["36-50"] += 1
            elif a.age <= 65:
                bins["51-65"] += 1
            else:
                bins["66+"] += 1
        return bins

    @staticmethod
    def get_role_analytics(agents: List[AdvancedAgent]) -> Dict[str, Dict[str, float]]:
        data = {}
        for a in agents:
            if not a.is_alive:
                continue
            if a.role not in data:
                data[a.role] = {"count": 0.0, "avg_money": 0.0, "avg_food": 0.0}
            data[a.role]["count"] += 1
            data[a.role]["avg_money"] += a.money
            data[a.role]["avg_food"] += a.food
            
        for role, stats in data.items():
            if stats["count"] > 0:
                stats["avg_money"] = round(stats["avg_money"] / stats["count"], 2)
                stats["avg_food"] = round(stats["avg_food"] / stats["count"], 2)
        return data
