import pytest
import os
import sys

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from simunation.agent import AdvancedAgent
from simunation.economy import AdvancedEconomy, MarketOrder
from simunation.relationships import RelationshipManager
from simunation.simulation import AdvancedSimulation

def test_agent_traits():
    agent = AdvancedAgent(agent_id=1, role="Farmer", x=10, y=10)
    assert agent.id == 1
    assert agent.role == "Farmer"
    assert agent.is_alive
    assert agent.health == 100.0
    assert agent.happiness > 0

def test_trust_relationships():
    rm = RelationshipManager()
    assert rm.get_trust(2) == 0.0
    
    rm.modify_trust(2, 25.0, "Successful deal", 1)
    assert rm.get_trust(2) == 25.0
    
    rm.modify_trust(2, -50.0, "Stole from me", 2)
    assert rm.get_trust(2) == -25.0
    
    memories = rm.get_memories_as_list()
    assert len(memories) == 2
    assert memories[0]["trustChange"] == -50

def test_economy_multimarket():
    economy = AdvancedEconomy()
    agents = {
        1: AdvancedAgent(agent_id=1, role="Worker", x=10, y=10),
        2: AdvancedAgent(agent_id=2, role="Farmer", x=10, y=10)
    }
    
    agents[1].money = 100.0
    agents[1].food = 0.0
    
    agents[2].money = 0.0
    agents[2].food = 10.0
    
    # Submit buy/sell food orders
    economy.submit_order(MarketOrder(agent_id=1, order_type="buy", item="food", amount=2.0, price=12.0))
    economy.submit_order(MarketOrder(agent_id=2, order_type="sell", item="food", amount=2.0, price=8.0))
    
    trades = economy.match_item_market("food", agents, 1)
    
    assert len(trades) == 1
    assert trades[0]["price"] == 10.0  # Midpoint
    assert agents[1].food == 2.0
    assert agents[2].food == 8.0
    assert agents[1].money == 80.0
    assert agents[2].money == 20.0

def test_simulation_run():
    sim = AdvancedSimulation()
    assert len(sim.agents) > 0
    res = sim.step()
    assert "stats" in res
    assert "logs" in res
    assert res["stats"]["timestep"] == 1
