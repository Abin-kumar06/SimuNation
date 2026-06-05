import pytest
from simunation.agent import Agent
from simunation.economy import Economy
from simunation.world import WorldEngine
from simunation.simulation import Simulation

def test_gini_coefficient():
    world = WorldEngine()
    
    # Set money levels to be equal
    for a in world.agents.values():
        a.money = 100.0
    
    # Perfect equality Gini should be 0.0
    assert world.calculate_gini() == 0.0

    # Set one agent to have all money, rest 0
    living_ids = [a.id for a in world.agents.values() if a.is_alive]
    for aid in living_ids:
        world.agents[aid].money = 0.0
    world.agents[living_ids[0]].money = 1000.0
    
    # Gini coefficient should be very high (approaching 1.0)
    assert world.calculate_gini() > 0.9

def test_market_matching():
    economy = Economy()
    
    # Create manual agents
    buyer = Agent(agent_id=1, role="Laborer", personality="cooperative")
    buyer.money = 100.0
    buyer.food = 0.0
    
    seller = Agent(agent_id=2, role="Farmer", personality="cooperative")
    seller.money = 0.0
    seller.food = 10.0
    
    agents = {1: buyer, 2: seller}
    
    # Submit matching orders
    economy.submit_orders([
        {"agent_id": 1, "type": "buy", "item": "food", "amount": 2.0, "price": 10.0},
        {"agent_id": 2, "type": "sell", "item": "food", "amount": 2.0, "price": 8.0}
    ])
    
    trades = economy.match_orders(agents)
    
    assert len(trades) == 1
    assert trades[0]["buyer_id"] == 1
    assert trades[0]["seller_id"] == 2
    assert trades[0]["amount"] == 2.0
    assert trades[0]["price"] == 9.0  # Midpoint of 10.0 and 8.0
    assert trades[0]["total"] == 18.0

    # Check resource update
    assert buyer.food == 2.0
    assert buyer.money == 82.0
    assert seller.food == 8.0
    assert seller.money == 18.0

def test_simulation_step():
    sim = Simulation()
    initial_alive = len([a for a in sim.world.agents.values() if a.is_alive])
    
    res = sim.step()
    
    # Verify stats keys exist
    assert "stats" in res
    assert "logs" in res
    assert "trades" in res
    assert res["stats"]["timestep"] == 1
