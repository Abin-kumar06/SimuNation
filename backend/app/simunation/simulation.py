import random
from typing import Dict, List, Any, Tuple
from simunation.config import config
from simunation.world import MapGrid
from simunation.agent import AdvancedAgent
from simunation.economy import AdvancedEconomy, MarketOrder
from simunation.government import Government
from simunation.events import EventManager
from simunation.families import FamilyRegistry
from simunation.analytics import AnalyticsManager

class AdvancedSimulation:
    def __init__(self):
        self.step_count: int = 0
        self.map: MapGrid = MapGrid()
        self.economy: AdvancedEconomy = AdvancedEconomy()
        self.government: Government = Government()
        self.events: EventManager = EventManager()
        self.families: FamilyRegistry = FamilyRegistry()
        self.agents: Dict[int, AdvancedAgent] = {}
        self.logs: List[str] = []
        self.history: List[Dict[str, Any]] = []
        self.total_thefts: int = 0
        self.next_agent_id: int = 1
        
        self._initialize_simulation()

    def _initialize_simulation(self):
        """Create initial agents and set up coordinates near relevant resources."""
        roles = ["Farmer", "Miner", "Builder", "Doctor", "Teacher", "Worker", "Trader", "Merchant"]
        weights = [0.25, 0.20, 0.15, 0.10, 0.10, 0.10, 0.05, 0.05]
        
        for _ in range(config.initial_population):
            role = random.choices(roles, weights=weights)[0]
            
            # Place agent near matching tile
            target_tile_type = "Town"
            if role == "Farmer":
                target_tile_type = "Farm"
            elif role == "Miner":
                target_tile_type = "Mine"
            
            # Find nearest tile or default random
            rx, ry = random.randint(0, 99), random.randint(0, 99)
            px, py = self.map.find_nearest_tile_type(rx, ry, target_tile_type)
            
            agent = AdvancedAgent(agent_id=self.next_agent_id, role=role, x=px, y=py)
            self.agents[agent.id] = agent
            self.next_agent_id += 1

    def step(self) -> Dict[str, Any]:
        self.step_count += 1
        step_logs = [f"--- Timestep {self.step_count} ---"]

        # 1. Step Events
        event_logs = self.events.step_events(self.step_count)
        step_logs.extend(event_logs)

        # 2. Agent Survival & Fatigue Consumption
        health_drain = self.events.get_multiplier("health_drain")
        for aid, agent in list(self.agents.items()):
            if agent.is_alive:
                # Apply event disease health drain if active
                if health_drain > 1.0:
                    agent.health = max(0.0, agent.health - health_drain * 3.0)
                    
                died, reason = agent.consume_resources()
                if died:
                    step_logs.append(f"💀 {agent.name} (#{agent.id}, {agent.role}) has died: {reason}.")

        # 3. Pathfinding / Movement Phase
        for aid, agent in self.agents.items():
            if not agent.is_alive:
                continue
            
            # Decides target
            if agent.energy < 35.0:
                # Go sleep in nearest town or stay put
                tx, ty = self.map.find_nearest_tile_type(agent.x, agent.y, "Town")
                agent.target_x, agent.target_y = tx, ty
            elif agent.role == "Farmer":
                tx, ty = self.map.find_nearest_tile_type(agent.x, agent.y, "Farm")
                agent.target_x, agent.target_y = tx, ty
            elif agent.role == "Miner":
                tx, ty = self.map.find_nearest_tile_type(agent.x, agent.y, "Mine")
                agent.target_x, agent.target_y = tx, ty
            else:
                # Seek Town centers
                tx, ty = self.map.find_nearest_tile_type(agent.x, agent.y, "Town")
                agent.target_x, agent.target_y = tx, ty
                
            agent.move_towards_target()

        # 4. Decisions, Work & Emergent Crime
        all_orders = []
        for aid, agent in self.agents.items():
            if not agent.is_alive:
                continue
                
            orders, crime = agent.make_decisions(self.economy.average_prices, self.step_count)
            all_orders.extend(orders)

            # Crime execution (Theft)
            if crime and crime["type"] == "theft":
                self._execute_theft(agent, step_logs)

        # 5. Economic Trade Matching
        for order in all_orders:
            self.economy.submit_order(MarketOrder(
                agent_id=order["agent_id"],
                order_type=order["type"],
                item=order["item"],
                amount=order["amount"],
                price=order["price"]
            ))

        # Match trades across all goods
        matched_trades = []
        for item in self.economy.average_prices:
            trades = self.economy.match_item_market(item, self.agents, self.step_count)
            matched_trades.extend(trades)

        # Limit transaction logging to notable trades
        for t in matched_trades[:12]:
            step_logs.append(f"🤝 {self.agents[t['buyer_id']].name} bought {t['amount']:.1f} {t['item']} from {self.agents[t['seller_id']].name} for ${t['total']:.2f}")

        # 6. Government Policy
        govt_logs = self.government.run_fiscal_cycle(self.agents, self.step_count)
        step_logs.extend(govt_logs)

        # 7. Demographics (Marriages & Childbirth)
        self._process_demographics(step_logs)

        # 8. Starvation memory alerts
        for aid, agent in self.agents.items():
            if agent.is_alive and agent.starvation_ticks == 1:
                self._record_memory(agent.id, agent.name, "I am starving because I have no food left! I must acquire food quickly.", 7)

        # 9. Record History Stats
        stats = self._compile_stats()

        # 10. LangGraph Government Council integration
        if self.step_count % 10 == 0:
            try:
                from simunation.agent_mind import run_government_council
                council_res = run_government_council({"stats": stats, "government": self.government.to_dict()}, step_logs)
                if council_res["policy"]:
                    p = council_res["policy"]
                    if "tax_rate" in p:
                        self.government.tax_rate = p["tax_rate"]
                    if "welfare_amount" in p:
                        self.government.welfare_amount = p["welfare_amount"]
                    step_logs.append(f"🏛️ Council: Adjusted policy - Tax: {self.government.tax_rate*100:.1f}%, Welfare: ${self.government.welfare_amount:.1f}. Analysis: {council_res['analysis']}")
                
                if council_res["event"]:
                    from simunation.events import WorldEvent
                    evt_name = council_res["event"]
                    events_config = {
                        "Drought": {"duration": 8, "description": "Council detected starvation crisis. Severe Drought initiated.", "modifiers": {"food_production": 0.4, "happiness": 0.85}},
                        "Economic Boom": {"duration": 10, "description": "Council detected low inequality. Initiated economic stimulus.", "modifiers": {"wage_multiplier": 1.5, "happiness": 1.25}}
                    }
                    if evt_name in events_config:
                        cfg = events_config[evt_name]
                        evt = WorldEvent(evt_name, cfg["duration"], cfg["description"], cfg["modifiers"])
                        self.events.active_events.append(evt)
                        step_logs.append(f"📢 Council Event: {evt_name} has been triggered by the Council!")
                # Compile stats again to capture policy update
                stats = self._compile_stats()
            except Exception as e:
                print(f"Error executing council agent: {e}")

        self.history.append(stats)
        if len(self.history) > 200:
            self.history.pop(0)

        self.logs.extend(step_logs)
        if len(self.logs) > 600:
            self.logs = self.logs[-600:]

        return {
            "stats": stats,
            "logs": step_logs,
            "trades": matched_trades
        }

    def _record_memory(self, agent_id: int, agent_name: str, text: str, importance: int):
        try:
            from simunation.database import add_agent_memory
            from simunation.agent_mind import get_embedding
            emb = get_embedding(text)
            add_agent_memory(agent_id, agent_name, self.step_count, text, importance, emb)
        except Exception as e:
            print(f"Error recording memory: {e}")

    def _execute_theft(self, thief: AdvancedAgent, step_logs: List[str]):
        """Executes a theft from a random wealthy neighbor on the same or adjacent tile."""
        neighbors = [
            a for a in self.agents.values() 
            if a.is_alive and a.id != thief.id and abs(a.x - thief.x) <= 3 and abs(a.y - thief.y) <= 3
        ]
        
        if neighbors:
            victim = max(neighbors, key=lambda x: x.money + x.food * 10)
            
            # Steal money and food
            stolen_money = round(victim.money * random.uniform(0.1, 0.3), 2)
            stolen_food = round(victim.food * random.uniform(0.1, 0.4), 2)
            
            victim.money -= stolen_money
            victim.food -= stolen_food
            victim.inventory["food"] = victim.food
            
            thief.money += stolen_money
            thief.food += stolen_food
            thief.inventory["food"] = thief.food
            
            self.total_thefts += 1
            
            # Betrayal destroys trust
            victim.relationships.modify_trust(thief.id, -60.0, f"Stole ${stolen_money} from me!", self.step_count)
            step_logs.append(f"⚠️ Crime: {thief.name} (#{thief.id}) robbed {victim.name} (#{victim.id}), stealing ${stolen_money:.1f} and {stolen_food:.1f} food.")
            
            # Record memories
            self._record_memory(thief.id, thief.name, f"I was starving and had to rob my neighbor {victim.name}, stealing ${stolen_money} and {stolen_food} food.", 8)
            self._record_memory(victim.id, victim.name, f"I was robbed by {thief.name}! They stole ${stolen_money} and {stolen_food} food from me. I do not trust them anymore.", 9)
        else:
            thief.last_action = "Failed theft (no targets nearby)"

    def _process_demographics(self, step_logs: List[str]):
        """Handles marriage proposals and childbirth of living couples."""
        # Find single adults
        singles = [a for a in self.agents.values() if a.is_alive and a.age >= 18 and a.partner_id is None]
        
        # Limit marriages per step to prevent population explosion
        random.shuffle(singles)
        marriages = 0
        
        for i in range(len(singles)):
            a1 = singles[i]
            if a1.partner_id is not None or a1.money < 60.0:
                continue
                
            for j in range(i + 1, len(singles)):
                a2 = singles[j]
                if a2.partner_id is not None or a2.money < 60.0:
                    continue
                
                # Check grid distance
                if abs(a1.x - a2.x) <= 4 and abs(a1.y - a2.y) <= 4:
                    # Marry
                    a1.partner_id = a2.id
                    a2.partner_id = a1.id
                    
                    # Create family unit
                    family = self.families.create_family([a1.id, a2.id], a1.x, a1.y)
                    a1.family_id = family.id
                    a2.family_id = family.id
                    
                    marriages += 1
                    step_logs.append(f"❤️ Marriage: {a1.name} and {a2.name} formed a partnership and started a family.")
                    
                    # Record memories
                    self._record_memory(a1.id, a1.name, f"I married my partner {a2.name} and we started our new family together.", 6)
                    self._record_memory(a2.id, a2.name, f"I married my partner {a1.name} and we started our new family together.", 6)
                    break
            if marriages >= 2:
                break

        # Childbirth chance for couples
        living_population = len([a for a in self.agents.values() if a.is_alive])
        if living_population >= config.max_population:
            return

        for a in list(self.agents.values()):
            if a.is_alive and a.partner_id is not None and a.family_id is not None:
                # Prevent double triggers (only trigger on one partner)
                if a.id < a.partner_id:
                    partner = self.agents[a.partner_id]
                    if partner.is_alive and a.money > 80.0 and len(a.children_ids) < 3:
                        # 4% chance per step
                        if random.random() < 0.04:
                            # Birth cost
                            a.money -= config.birth_cost_money / 2
                            partner.money -= config.birth_cost_money / 2
                            
                            # Spawn Child agent
                            child_id = self.next_agent_id
                            self.next_agent_id += 1
                            
                            child = AdvancedAgent(agent_id=child_id, role="Child", x=a.x, y=a.y)
                            child.age = 0
                            child.money = 0.0
                            child.food = 5.0
                            child.family_id = a.family_id
                            
                            self.agents[child_id] = child
                            
                            a.children_ids.append(child_id)
                            partner.children_ids.append(child_id)
                            
                            # Add member to family object
                            fam = self.families.families[a.family_id]
                            fam.add_member(child_id)
                            
                            step_logs.append(f"👶 Birth: A new child, {child.name}, was born to {a.name} and {partner.name}.")
                            
                            # Record memories
                            self._record_memory(a.id, a.name, f"Our new child, {child.name}, was born! I am so happy to expand our family.", 8)
                            self._record_memory(partner.id, partner.name, f"Our new child, {child.name}, was born! I am so happy to expand our family.", 8)

    def _compile_stats(self) -> Dict[str, Any]:
        living = [a for a in self.agents.values() if a.is_alive]
        dead_count = sum(1 for a in self.agents.values() if not a.is_alive)
        starving_count = sum(1 for a in living if a.starvation_ticks > 0)
        
        age_dist = AnalyticsManager.get_age_distribution(living)
        role_stats = AnalyticsManager.get_role_analytics(living)
        gini = AnalyticsManager.calculate_gini(living)
        
        tot_money = sum(a.money for a in living) + self.government.treasury
        tot_food = sum(a.food for a in living)
        
        active_event_names = [e.name for e in self.events.active_events]

        return {
            "timestep": self.step_count,
            "population_alive": len(living),
            "population_starving": starving_count,
            "population_dead": dead_count,
            "gini_coefficient": gini,
            "total_money": round(tot_money, 2),
            "total_food": round(tot_food, 2),
            "average_food_price": self.economy.get_avg_price("food"),
            "crime_thefts": self.total_thefts,
            "age_distribution": age_dist,
            "role_analytics": role_stats,
            "government": self.government.to_dict(),
            "active_events": active_event_names
        }

    def reset(self):
        self.step_count = 0
        self.economy = AdvancedEconomy()
        self.government = Government()
        self.events = EventManager()
        self.families = FamilyRegistry()
        self.agents = {}
        self.logs = ["Civilization reset."]
        self.history = []
        self.total_thefts = 0
        self._initialize_simulation()
