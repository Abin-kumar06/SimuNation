from typing import List, Dict, Any
from simunation.config import config
from simunation.world import WorldEngine
from simunation.economy import Economy

class Simulation:
    def __init__(self):
        self.world = WorldEngine()
        self.economy = Economy()
        self.logs: List[str] = []

    def step(self) -> Dict[str, Any]:
        """Advance the simulation by one timestep."""
        self.world.timestep += 1
        step_logs = [f"--- Timestep {self.world.timestep} ---"]
        
        # 1. Consumption Phase
        for agent_id, agent in list(self.world.agents.items()):
            if agent.is_alive:
                status = agent.consume_food()
                if status == "Starving":
                    step_logs.append(f"⚠️ Agent {agent_id} ({agent.role}) is starving! (Food: {agent.food:.1f})")
                elif status == "Died":
                    step_logs.append(f"💀 Agent {agent_id} ({agent.role}) has died of starvation.")

        # 2. Production Phase
        for agent_id, agent in self.world.agents.items():
            if agent.is_alive:
                produced = agent.produce()
                # We can optionally log production details if significant

        # 3. Market Phase
        # Gather all bids and asks
        all_orders = []
        for agent_id, agent in self.world.agents.items():
            if agent.is_alive:
                orders = agent.make_decisions(self.economy.current_average_price)
                all_orders.extend(orders)

        self.economy.submit_orders(all_orders)
        trades = self.economy.match_orders(self.world.agents)
        
        for trade in trades:
            log_msg = (
                f"🤝 Agent {trade['buyer_id']} ({trade['buyer_role']}) bought "
                f"{trade['amount']:.1f} food from Agent {trade['seller_id']} "
                f"({trade['seller_role']}) at ${trade['price']:.2f}/unit "
                f"(Total: ${trade['total']:.2f})"
            )
            step_logs.append(log_msg)

        # Log food shortage if demand wasn't met (no matched trades or high average price)
        # Let's count unmatched buy orders to detect food shortage
        unmatched_buy_volume = sum(order["amount"] for order in all_orders if order["type"] == "buy")
        matched_volume = sum(trade["amount"] for trade in trades)
        if unmatched_buy_volume > matched_volume * 1.5 and unmatched_buy_volume > 5.0:
            step_logs.append("⚠️ Food shortage detected! High demand, low supply in the market.")

        # 4. Tax and Welfare Phase
        collected_taxes = self.world.collect_taxes()
        distributed_welfare = self.world.distribute_welfare()
        if collected_taxes > 0 or distributed_welfare > 0:
            step_logs.append(f"🏛️ Govt: Collected ${collected_taxes:.2f} in taxes. Distributed ${distributed_welfare:.2f} in welfare.")

        # 5. Compile Statistics
        stats = self.world.get_stats(self.economy.current_average_price)
        self.world.record_history(stats)
        
        # Save step logs
        self.logs.extend(step_logs)
        # Keep logs list reasonable in size
        if len(self.logs) > 500:
            self.logs = self.logs[-500:]

        return {
            "stats": stats,
            "logs": step_logs,
            "trades": trades
        }
        
    def reset(self):
        """Reset simulation state."""
        self.world = WorldEngine()
        self.economy = Economy()
        self.logs = ["Simulation reset."]
