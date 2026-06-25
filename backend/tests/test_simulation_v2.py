import pytest
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from simunation.simulation import Simulation
from simunation.agent import Agent, Profession, ActionType
from simunation.world import World, TileType
from simunation.relationships import SocialEngine
from simunation.families import FamilySystem
from simunation.government import Government


class TestWorld:
    def test_world_initialization(self):
        world = World(width=50, height=50, seed=42)
        assert world.width == 50
        assert world.height == 50
        assert len(world.grid) == 50
        assert len(world.grid[0]) == 50

    def test_tile_types_exist(self):
        world = World(width=20, height=20, seed=42)
        types = set()
        for row in world.grid:
            for tile in row:
                types.add(tile.tile_type)
        assert len(types) > 3

    def test_gini_empty(self):
        world = World(width=10, height=10)
        assert world.calculate_gini() == 0.0

    def test_gini_inequality(self):
        world = World(width=10, height=10)
        Agent(x=0, y=0, world=world, age=25)
        Agent(x=1, y=1, world=world, age=25)
        world.agents[1].money = 100
        world.agents[2].money = 0
        gini = world.calculate_gini()
        assert 0 < gini < 1

    def test_spatial_hashing_neighbors(self):
        world = World(width=20, height=20, seed=42)
        neighbors = world.get_neighbors(10, 10, radius=1)
        assert len(neighbors) == 5  # center + 4 cardinal (Manhattan)

    def test_agent_movement_between_tiles(self):
        world = World(width=20, height=20, seed=42)
        agent = Agent(x=5, y=5, world=world, age=25)
        old_tile = world.get_tile(5, 5)
        assert agent.id in old_tile.agents_here

        world.move_agent(agent.id, 5, 5, 6, 6)
        new_tile = world.get_tile(6, 6)
        assert agent.id not in old_tile.agents_here
        assert agent.id in new_tile.agents_here


class TestAgent:
    def test_agent_creation(self):
        world = World(width=10, height=10, seed=42)
        agent = Agent(x=5, y=5, world=world, age=25)
        assert agent.alive
        assert agent.age == 25
        assert agent.id in world.agents
        assert agent.food > 0

    def test_trait_inheritance(self):
        world = World(width=10, height=10, seed=42)
        parent = Agent(x=5, y=5, world=world, age=30)
        child = Agent(x=5, y=5, world=world, age=0, is_child=True, inherited_traits=parent.traits)
        assert abs(child.traits.greed - parent.traits.greed) < 0.3
        assert abs(child.traits.cooperation - parent.traits.cooperation) < 0.3

    def test_perception(self):
        world = World(width=20, height=20, seed=42)
        agent = Agent(x=10, y=10, world=world, age=25)
        perception = agent.perceive()
        assert "current_tile" in perception
        assert "nearby_agents" in perception
        assert "self_state" in perception

    def test_decision_utility(self):
        world = World(width=20, height=20, seed=42)
        agent = Agent(x=10, y=10, world=world, age=25)
        perception = agent.perceive()
        action, params = agent.decide(perception)
        assert isinstance(action, ActionType)
        assert isinstance(params, dict)

    def test_decision_when_starving(self):
        world = World(width=20, height=20, seed=42)
        agent = Agent(x=10, y=10, world=world, age=25)
        agent.food = 5  # Starving
        perception = agent.perceive()
        action, params = agent.decide(perception)
        assert action in (ActionType.PRODUCE, ActionType.TRADE, ActionType.MOVE, ActionType.STEAL)

    def test_metabolism(self):
        world = World(width=10, height=10, seed=42)
        agent = Agent(x=5, y=5, world=world, age=25)
        initial_food = agent.food
        agent.update_metabolism()
        assert agent.food < initial_food
        assert agent.age > 25

    def test_death_by_health(self):
        world = World(width=10, height=10, seed=42)
        agent = Agent(x=5, y=5, world=world, age=85)
        agent.health = 0
        agent.update_metabolism()
        assert not agent.alive
        tile = world.get_tile(5, 5)
        assert agent.id not in tile.agents_here

    def test_child_growth(self):
        world = World(width=10, height=10, seed=42)
        agent = Agent(x=5, y=5, world=world, age=0, is_child=True)
        assert agent.profession == Profession.CHILD
        agent.age = 18
        agent.update_metabolism()
        assert not agent.is_child
        assert agent.profession != Profession.CHILD

    def test_memory_system(self):
        world = World(width=10, height=10, seed=42)
        agent = Agent(x=5, y=5, world=world, age=25)
        agent._add_memory("test_event", {"detail": "test"}, 0.5)
        assert len(agent.memory) == 1
        assert agent.memory[0].event_type == "test_event"

    def test_memory_capacity(self):
        world = World(width=10, height=10, seed=42)
        agent = Agent(x=5, y=5, world=world, age=25)
        for i in range(100):
            agent._add_memory("event", {"i": i}, 0.1)
        assert len(agent.memory) <= agent.memory_capacity

    def test_trust_update(self):
        world = World(width=10, height=10, seed=42)
        agent = Agent(x=5, y=5, world=world, age=25)
        agent._update_trust(999, 0.5)
        assert agent.trust_scores[999] == 0.5
        agent._update_trust(999, -0.3)
        assert agent.trust_scores[999] == 0.2

    def test_trust_bounds(self):
        world = World(width=10, height=10, seed=42)
        agent = Agent(x=5, y=5, world=world, age=25)
        agent._update_trust(1, 5.0)
        assert agent.trust_scores[1] == 1.0
        agent._update_trust(2, -5.0)
        assert agent.trust_scores[2] == -1.0

    def test_reproduction_requirements(self):
        world = World(width=20, height=20, seed=42)
        parent1 = Agent(x=5, y=5, world=world, age=30)
        parent2 = Agent(x=5, y=5, world=world, age=30)
        parent1.partner_id = parent2.id
        parent2.partner_id = parent1.id
        parent1.money = 100
        parent2.money = 100

        # Should succeed with high probability over many attempts
        children = []
        for _ in range(500):
            child = parent1.reproduce()
            if child:
                children.append(child)

        assert len(children) > 0

    def test_child_has_parents(self):
        world = World(width=20, height=20, seed=42)
        parent1 = Agent(x=5, y=5, world=world, age=30)
        parent2 = Agent(x=5, y=5, world=world, age=30)
        parent1.partner_id = parent2.id
        parent2.partner_id = parent1.id
        parent1.money = 100
        parent2.money = 100

        child = None
        for _ in range(1000):
            child = parent1.reproduce()
            if child:
                break

        assert child is not None
        assert parent1.id in child.parents
        assert parent2.id in child.parents
        assert child.id in parent1.children_ids
        assert child.id in parent2.children_ids


class TestSimulation:
    def test_simulation_init(self):
        sim = Simulation(width=50, height=50, initial_population=20, seed=42)
        assert sim.world is not None
        assert len([a for a in sim.world.agents.values() if a.alive]) == 20

    def test_simulation_step(self):
        sim = Simulation(width=50, height=50, initial_population=10, seed=42)
        result = sim.step()
        assert "stats" in result
        assert "logs" in result
        assert result["stats"]["timestep"] == 1

    def test_multiple_steps(self):
        sim = Simulation(width=50, height=50, initial_population=10, seed=42)
        history = sim.run(steps=5)
        assert len(history) == 5
        assert history[-1]["stats"]["timestep"] == 5

    def test_stats_tracking(self):
        sim = Simulation(width=50, height=50, initial_population=10, seed=42)
        result = sim.step()
        stats = result["stats"]
        assert "population_alive" in stats
        assert "population_starving" in stats
        assert "gini_coefficient" in stats
        assert "average_food_price" in stats

    def test_scenario_famine(self):
        sim = Simulation(width=50, height=50, initial_population=10, seed=42)
        initial_food = sum(
            tile.resources.get("food", 0)
            for row in sim.world.grid
            for tile in row
            if tile.tile_type == TileType.FARM
        )
        logs = sim.apply_scenario("famine", {"intensity": 0.5})
        assert len(logs) > 0
        after_food = sum(
            tile.resources.get("food", 0)
            for row in sim.world.grid
            for tile in row
            if tile.tile_type == TileType.FARM
        )
        assert after_food < initial_food

    def test_scenario_ubi(self):
        sim = Simulation(width=50, height=50, initial_population=10, seed=42)
        initial_wealth = sum(a.money for a in sim.world.agents.values() if a.alive)
        sim.apply_scenario("ubi", {"amount": 50})
        after_wealth = sum(a.money for a in sim.world.agents.values() if a.alive)
        assert after_wealth > initial_wealth

    def test_scenario_plague(self):
        sim = Simulation(width=50, height=50, initial_population=50, seed=42)
        initial_alive = len([a for a in sim.world.agents.values() if a.alive])
        logs = sim.apply_scenario("plague", {"mortality": 0.2})
        after_alive = len([a for a in sim.world.agents.values() if a.alive])
        assert after_alive < initial_alive

    def test_government_adaptation(self):
        sim = Simulation(width=50, height=50, initial_population=20, seed=42)
        initial_rate = sim.government.policy.tax_rate

        # Starve agents to trigger policy change
        for agent in sim.world.agents.values():
            agent.food = 5

        for _ in range(15):
            sim.step()

        assert (
            len(sim.government.policy_history) > 0
            or sim.government.policy.tax_rate != initial_rate
        )

    def test_market_prices_update(self):
        sim = Simulation(width=50, height=50, initial_population=10, seed=42)
        initial_price = sim.world.get_price("food")
        sim.step()
        new_price = sim.world.get_price("food")
        assert new_price > 0

    def test_agent_diary(self):
        sim = Simulation(width=50, height=50, initial_population=5, seed=42)
        sim.run(steps=3)
        agent_id = list(sim.world.agents.keys())[0]
        diary = sim.get_agent_diary(agent_id)
        assert "diary_entries" in diary
        assert "summary" in diary
        assert "traits" in diary


class TestTrade:
    def test_trade_buy(self):
        world = World(width=20, height=20, seed=42)
        buyer = Agent(x=5, y=5, world=world, age=25)
        seller = Agent(x=6, y=6, world=world, age=25)

        buyer.food = 10
        buyer.money = 100
        seller.food = 80
        seller.money = 50

        initial_buyer_money = buyer.money
        initial_seller_money = seller.money

        logs = buyer._execute_trade(seller, "buy")
        assert len(logs) > 0
        assert buyer.food > 10
        assert buyer.money < initial_buyer_money
        assert seller.money > initial_seller_money

    def test_trade_sell(self):
        world = World(width=20, height=20, seed=42)
        seller = Agent(x=5, y=5, world=world, age=25)
        buyer = Agent(x=6, y=6, world=world, age=25)

        seller.food = 80
        seller.money = 50
        buyer.food = 20
        buyer.money = 100

        initial_seller_food = seller.food
        logs = seller._execute_trade(buyer, "sell")
        assert len(logs) > 0
        assert seller.food < initial_seller_food

    def test_trade_trust_increase(self):
        world = World(width=20, height=20, seed=42)
        buyer = Agent(x=5, y=5, world=world, age=25)
        seller = Agent(x=6, y=6, world=world, age=25)

        buyer.food = 10
        buyer.money = 100
        seller.food = 80
        seller.money = 50

        initial_trust = buyer.trust_scores.get(seller.id, 0.0)
        buyer._execute_trade(seller, "buy")
        assert buyer.trust_scores[seller.id] > initial_trust

    def test_crime_success(self):
        world = World(width=20, height=20, seed=42)
        criminal = Agent(x=5, y=5, world=world, age=25)
        victim = Agent(x=5, y=5, world=world, age=25)

        criminal.traits.greed = 1.0
        criminal.traits.aggression = 1.0
        criminal.traits.honor = 0.0
        victim.money = 100

        initial_victim_money = victim.money
        logs = criminal._execute_crime(victim)

        assert len(logs) > 0
        assert "CRIME" in logs[0]
        assert victim.money < initial_victim_money
        assert criminal.trust_scores[victim.id] < 0

    def test_crime_reputation_damage(self):
        world = World(width=20, height=20, seed=42)
        criminal = Agent(x=5, y=5, world=world, age=25)
        victim = Agent(x=5, y=5, world=world, age=25)
        witness = Agent(x=5, y=5, world=world, age=25)

        criminal.traits.greed = 1.0
        criminal.traits.aggression = 1.0
        criminal.traits.honor = 0.0
        victim.money = 100

        criminal._execute_crime(victim)
        assert witness.subjective_reputations.get(criminal.id, 0.0) < 0


class TestGovernment:
    def test_tax_collection(self):
        world = World(width=20, height=20, seed=42)
        gov = Government(world)
        Agent(x=5, y=5, world=world, age=25, is_child=False)
        Agent(x=6, y=6, world=world, age=25, is_child=False)

        initial_treasury = gov.treasury
        collected = gov.collect_taxes()
        assert collected > 0
        assert gov.treasury > initial_treasury

    def test_welfare_distribution(self):
        world = World(width=20, height=20, seed=42)
        gov = Government(world)
        poor_agent = Agent(x=5, y=5, world=world, age=25, is_child=False)
        poor_agent.food = 5
        poor_agent.money = 0

        gov.treasury = 100
        logs = gov.distribute_welfare()
        assert len(logs) > 0

    def test_adaptive_policy(self):
        world = World(width=20, height=20, seed=42)
        gov = Government(world)
        initial_rate = gov.policy.tax_rate

        for _ in range(5):
            agent = Agent(x=5, y=5, world=world, age=25, is_child=False)
            agent.food = 5

        gov.adapt_policy()
        assert len(gov.policy_history) > 0 or gov.policy.tax_rate != initial_rate


class TestSocialEngine:
    def test_bond_formation(self):
        world = World(width=20, height=20, seed=42)
        engine = SocialEngine(world)
        engine.update_bond(1, 2, 0.5, "friend")
        bond = engine.get_bond(1, 2)
        assert bond is not None
        assert bond.strength == 0.5

    def test_bond_decay(self):
        world = World(width=20, height=20, seed=42)
        world.timestep = 100
        engine = SocialEngine(world)
        engine.update_bond(1, 2, 0.5, "friend")
        world.timestep = 200
        engine.decay_bonds()
        bond = engine.get_bond(1, 2)
        assert bond is None or bond.strength < 0.5


class TestFamilySystem:
    def test_household_formation(self):
        world = World(width=20, height=20, seed=42)
        family = FamilySystem(world)
        agent1 = Agent(x=5, y=5, world=world, age=25)
        agent2 = Agent(x=5, y=5, world=world, age=25)

        hid = family.form_household(agent1.id, agent2.id)
        assert hid is not None
        assert agent1.id in family.households[hid]
        assert agent2.id in family.households[hid]

    def test_resource_sharing(self):
        world = World(width=20, height=20, seed=42)
        family = FamilySystem(world)
        agent1 = Agent(x=5, y=5, world=world, age=25)
        agent2 = Agent(x=5, y=5, world=world, age=25)

        family.form_household(agent1.id, agent2.id)
        agent1.food = 100
        agent2.food = 0

        family.household_resource_sharing()
        assert agent2.food > 0
