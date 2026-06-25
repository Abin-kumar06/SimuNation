import random
from typing import List, Dict, Optional
from .world import World, TileType
from .agent import Agent, Profession
from .government import Government
from .relationships import SocialEngine
from .families import FamilySystem
from .infrastructure import InfrastructureManager


class Simulation:
    def __init__(self, width: int = 100, height: int = 100, initial_population: int = 50, seed: Optional[int] = None):
        self.world = World(width=width, height=height, seed=seed)
        self.infrastructure = InfrastructureManager(self.world)
        self.government = Government(self.world)
        self.social_engine = SocialEngine(self.world)
        self.family_system = FamilySystem(self.world)

        self._initialize_population(initial_population)
        self.paused = False
        self.speed = 1.0
        self.history: List[Dict[str, Any]] = []
        self.logs: List[str] = []

    def _initialize_population(self, count: int):
        """Create initial agents scattered across the world"""
        for _ in range(count):
            attempts = 0
            while attempts < 100:
                x = random.randint(0, self.world.width - 1)
                y = random.randint(0, self.world.height - 1)
                tile = self.world.get_tile(x, y)
                if tile and tile.tile_type in (TileType.VILLAGE, TileType.TOWN, TileType.FARM):
                    break
                attempts += 1

            age = random.gauss(30, 15)
            age = max(18, min(60, age))

            agent = Agent(
                x=x, y=y,
                world=self.world,
                age=age,
                is_child=False,
            )

            # Initialize some starting trust between nearby agents
            nearby = self.world.get_agents_in_radius(x, y, 5)
            for aid in nearby:
                if aid != agent.id:
                    agent.trust_scores[aid] = random.gauss(0.3, 0.2)

    def step(self) -> Dict:
        """Execute one simulation timestep"""
        self.world.timestep += 1

        # Reset per-step counters
        self.world._births_this_step = 0
        self.world._deaths_this_step = 0
        self.world._crimes_this_step = 0
        self.world._trades_this_step = 0

        logs = []
        new_agents = []

        # 1. Government actions (taxes, welfare, policy)
        gov_logs = self.government.step()
        logs.extend(gov_logs)

        # 2. Agent decisions and actions
        alive_agents = [a for a in self.world.agents.values() if a.alive]

        # Shuffle to prevent ordering bias
        random.shuffle(alive_agents)

        for agent in alive_agents:
            # Perception
            perception = agent.perceive()

            # Cognition
            action, params = agent.decide(perception)

            # Action
            action_logs = agent.act(action, params)
            logs.extend(action_logs)

            # Metabolism and aging
            agent.update_metabolism()

            # Reproduction
            if not agent.is_child and agent.alive and agent.partner_id:
                child = agent.reproduce()
                if child:
                    new_agents.append(child)
                    self.family_system.add_child_to_household(child.id, agent.id)
                    logs.append(f"BIRTH: Agent {child.id} born to Agent {agent.id} and Agent {agent.partner_id}")

        # 3. Social dynamics
        social_logs = self.social_engine.step()
        logs.extend(social_logs)

        # 4. Family dynamics
        family_logs = self.family_system.step()
        logs.extend(family_logs)

        # 5. Infrastructure and vehicles update
        self.infrastructure.update_vehicles()
        for agent in alive_agents:
            if agent.profession.name in ('TRADER', 'MERCHANT') and random.random() < 0.1:
                start = (agent.x, agent.y)
                destinations = list(self.infrastructure.settlement_centers.values())
                if destinations:
                    end = random.choice(destinations)
                    self.infrastructure.spawn_vehicle(start, end, "truck" if random.random() < 0.3 else "car")

        # 6. Market update
        self.world.update_market_prices()

        # 6. Add new agents to world
        for child in new_agents:
            self.world.agents[child.id] = child

        # Compile stats
        stats = self.world.get_stats()

        # Add government state to stats
        stats["government"] = self.government.to_dict()

        self.history.append(stats)
        if len(self.history) > 200:
            self.history.pop(0)

        self.logs.extend(logs)
        if len(self.logs) > 600:
            self.logs = self.logs[-600:]

        return {
            "timestep": self.world.timestep,
            "stats": stats,
            "logs": logs,
            "agents": [a.to_dict() for a in self.world.agents.values() if a.alive],
            "world": self.world.to_dict(),
        }

    def run(self, steps: int) -> List[Dict]:
        """Run multiple steps and return history"""
        history = []
        for _ in range(steps):
            result = self.step()
            history.append(result)
        return history

    def apply_scenario(self, scenario_type: str, params: Dict) -> List[str]:
        """Apply external scenario/policy change"""
        logs = []

        if scenario_type == "famine":
            intensity = params.get("intensity", 0.5)
            for row in self.world.grid:
                for tile in row:
                    if tile.tile_type == TileType.FARM:
                        tile.resources["food"] *= (1 - intensity)
            logs.append(f"SCENARIO: Famine reduces farm output by {intensity:.0%}")

        elif scenario_type == "gold_rush":
            for row in self.world.grid:
                for tile in row:
                    if tile.tile_type == TileType.MINE:
                        tile.resources["minerals"] *= 2.0
                        tile.resources["raw_materials"] *= 1.5
            logs.append("SCENARIO: Gold rush! Mineral deposits doubled.")

        elif scenario_type == "plague":
            mortality = params.get("mortality", 0.1)
            alive = [a for a in self.world.agents.values() if a.alive]
            victims = random.sample(alive, int(len(alive) * mortality))
            for victim in victims:
                victim.health = 0
                victim.alive = False
            logs.append(f"SCENARIO: Plague killed {len(victims)} agents")

        elif scenario_type == "tax_reform":
            self.government.policy.tax_rate = params.get("tax_rate", 0.15)
            logs.append(f"SCENARIO: Tax rate changed to {self.government.policy.tax_rate:.0%}")

        elif scenario_type == "ubi":
            amount = params.get("amount", 10.0)
            for agent in self.world.agents.values():
                if agent.alive and not agent.is_child:
                    agent.money += amount
                    self.government.treasury -= amount
            logs.append(f"SCENARIO: UBI of ${amount} distributed to all citizens")

        elif scenario_type == "migration_wave":
            count = params.get("count", 10)
            for _ in range(count):
                x = random.randint(0, self.world.width - 1)
                y = random.randint(0, self.world.height - 1)
                agent = Agent(x=x, y=y, world=self.world, age=random.randint(20, 40), is_child=False)
                agent.money = 30
            logs.append(f"SCENARIO: Migration wave of {count} new agents")

        return logs

    def get_agent_diary(self, agent_id: int) -> Dict:
        """Generate narrative from agent's memory"""
        agent = self.world.agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}

        diary = []
        for mem in agent.memory:
            entry = f"Year {mem.timestep // 10}: {mem.event_type}"
            if mem.emotional_valence > 0.5:
                entry += " (joyful)"
            elif mem.emotional_valence < -0.5:
                entry += " (traumatic)"
            elif mem.emotional_valence < 0:
                entry += " (unpleasant)"
            else:
                entry += " (neutral)"

            if "partner" in mem.details:
                entry += f" with Agent {mem.details['partner']}"
            if "stolen" in mem.details:
                entry += f" — lost ${mem.details['stolen']:.1f}"

            diary.append(entry)

        summary = f"Agent {agent_id}, a {agent.profession.name}, lived {agent.age:.1f} years."
        if agent.partner_id:
            summary += f" Partnered with Agent {agent.partner_id}."
        summary += f" Had {len(agent.children_ids)} children."
        if not agent.alive:
            summary += " Deceased."

        return {
            "agent_id": agent_id,
            "alive": agent.alive,
            "summary": summary,
            "diary_entries": diary,
            "traits": {
                "greed": round(agent.traits.greed, 2),
                "cooperation": round(agent.traits.cooperation, 2),
                "intelligence": round(agent.traits.intelligence, 2),
                "honor": round(agent.traits.honor, 2),
            },
            "final_stats": {
                "money": round(agent.money, 1),
                "food": round(agent.food, 1),
                "health": round(agent.health, 1),
                "happiness": round(agent.happiness, 1),
            } if not agent.alive else None,
        }

    def reset(self):
        """Reset the simulation state"""
        self.world = World(width=self.world.width, height=self.world.height)
        self.infrastructure = InfrastructureManager(self.world)
        self.government = Government(self.world)
        self.social_engine = SocialEngine(self.world)
        self.family_system = FamilySystem(self.world)
        self.history = []
        self.logs = ["Simulation reset."]
        self._initialize_population(50)

