from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List

from simunation.simulation import AdvancedSimulation

app = FastAPI(title="SimuNation V2 — Emergent AI Civilization Simulator")

# Enable CORS for React dev server on port 5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Simulation Instance
sim = AdvancedSimulation()

class PolicyUpdate(BaseModel):
    tax_rate: float
    welfare_amount: float
    welfare_money_threshold: float
    welfare_food_threshold: float

@app.get("/api/map")
async def get_map():
    """Retrieve the static geographic map grid layout (100x100)."""
    grid_data = []
    for y in range(sim.map.height):
        row = []
        for x in range(sim.map.width):
            row.append(sim.map.get_tile(x, y).type)
        grid_data.append(row)
    return {
        "width": sim.map.width,
        "height": sim.map.height,
        "grid": grid_data
    }

@app.get("/api/state")
async def get_state():
    """Retrieve full civilization stats, logs, active events, and compressed agent coordinates."""
    living_agents = []
    dead_agents = []
    
    for aid, agent in sim.agents.items():
        agent_data = {
            "id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "age": agent.age,
            "money": round(agent.money, 2),
            "food": round(agent.food, 2),
            "health": round(agent.health, 1),
            "energy": round(agent.energy, 1),
            "happiness": round(agent.happiness, 1),
            "housing": agent.housing_level,
            "x": agent.x,
            "y": agent.y,
            "is_alive": agent.is_alive,
            "starving": agent.starvation_ticks > 0,
            "last_action": agent.last_action,
            "children_count": len(agent.children_ids)
        }
        if agent.is_alive:
            living_agents.append(agent_data)
        else:
            dead_agents.append(agent_data)
            
    latest_stats = {}
    if sim.history:
        latest_stats = sim.history[-1]
    else:
        latest_stats = sim._compile_stats()

    return {
        "stats": latest_stats,
        "history": sim.history,
        "agents": living_agents + dead_agents,
        "logs": sim.logs[-150:],  # Send last 150 items
        "government": sim.government.to_dict()
    }

@app.post("/api/step")
async def step_simulation(count: int = Query(1, description="Number of steps to execute")):
    if count < 1:
        raise HTTPException(status_code=400, detail="Count must be at least 1")
    
    last_res = None
    for _ in range(count):
        last_res = sim.step()
        
    return {
        "success": True,
        "steps_run": count,
        "stats": last_res["stats"] if last_res else None,
        "logs": last_res["logs"] if last_res else []
    }

@app.post("/api/reset")
async def reset_simulation():
    sim.reset()
    return {"success": True, "message": "Civilization reset completed."}

@app.post("/api/policy")
async def update_policy(policy: PolicyUpdate):
    sim.government.tax_rate = policy.tax_rate
    sim.government.welfare_amount = policy.welfare_amount
    sim.government.welfare_money_threshold = policy.welfare_money_threshold
    sim.government.welfare_food_threshold = policy.welfare_food_threshold
    return {"success": True, "message": "Government fiscal policies updated."}

@app.post("/api/trigger-event")
async def trigger_event(name: str):
    """Admin endpoint to manually inject world events."""
    valid_events = ["Drought", "Disease Outbreak", "Economic Boom", "Resource Discovery", "Market Crash"]
    if name not in valid_events:
        raise HTTPException(status_code=400, detail=f"Invalid event. Must be one of {valid_events}")
        
    # Get config properties
    events_config = {
        "Drought": {
            "duration": 8,
            "description": "Admin manually triggered a severe Drought. Crops will dry out.",
            "modifiers": {"food_production": 0.4, "happiness": 0.85}
        },
        "Disease Outbreak": {
            "duration": 6,
            "description": "Admin manually released a pathogen. Health levels are falling.",
            "modifiers": {"health_drain": 2.0, "happiness": 0.75}
        },
        "Economic Boom": {
            "duration": 10,
            "description": "Admin manual stimulus. Higher wages and employee satisfaction.",
            "modifiers": {"wage_multiplier": 1.5, "happiness": 1.25}
        },
        "Resource Discovery": {
            "duration": 5,
            "description": "Admin manual resource spawn, doubling mining outputs.",
            "modifiers": {"mine_production": 2.5}
        },
        "Market Crash": {
            "duration": 7,
            "description": "Admin manual stock-panic. Prices drop.",
            "modifiers": {"price_deflation": 0.7, "happiness": 0.8}
        }
    }
    
    cfg = events_config[name]
    from simunation.events import WorldEvent
    evt = WorldEvent(name, cfg["duration"], cfg["description"], cfg["modifiers"])
    sim.events.active_events.append(evt)
    sim.logs.append(f"📢 Event Alert: {name} has been manually started by Government! {cfg['description']}")
    return {"success": True, "message": f"Event '{name}' started."}
