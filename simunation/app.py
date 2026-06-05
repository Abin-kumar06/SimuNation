import os
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Any, List

from simunation.config import config, SimConfig
from simunation.simulation import Simulation

app = FastAPI(title="SimuNation — Emergent AI Civilization Simulator")

# Global simulation instance
sim = Simulation()

class ConfigUpdate(BaseModel):
    tax_rate: float
    welfare_threshold_money: float
    welfare_threshold_food: float
    farmer_food_production_per_step: float
    laborer_wage_per_step: float

@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the single-page visualization dashboard."""
    # Find template relative to app file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(current_dir, "templates", "index.html")
    
    if not os.path.exists(template_path):
        raise HTTPException(status_code=404, detail="Dashboard template not found")
        
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return html_content

@app.get("/api/state")
async def get_state():
    """Retrieve current state of the simulation, including agents, history, and current parameters."""
    living_agents = []
    dead_agents = []
    
    for agent_id, agent in sim.world.agents.items():
        agent_data = {
            "id": agent.id,
            "role": agent.role,
            "personality": agent.personality,
            "money": round(agent.money, 2),
            "food": round(agent.food, 2),
            "starvation_steps": agent.starvation_steps,
            "is_alive": agent.is_alive,
            "last_action": agent.last_action,
            "perceived_value": round(agent.perceived_value, 2)
        }
        if agent.is_alive:
            living_agents.append(agent_data)
        else:
            dead_agents.append(agent_data)
            
    # Sort agents by ID
    living_agents.sort(key=lambda x: x["id"])
    dead_agents.sort(key=lambda x: x["id"])
            
    latest_stats = {}
    if sim.world.history:
        latest_stats = sim.world.history[-1]
    else:
        # Default stats if not started
        latest_stats = sim.world.get_stats(sim.economy.current_average_price)

    return {
        "stats": latest_stats,
        "history": sim.world.history,
        "living_agents": living_agents,
        "dead_agents": dead_agents,
        "logs": sim.logs[-100:],  # Return last 100 log items
        "config": {
            "tax_rate": config.tax_rate,
            "welfare_threshold_money": config.welfare_threshold_money,
            "welfare_threshold_food": config.welfare_threshold_food,
            "farmer_food_production_per_step": config.farmer_food_production_per_step,
            "laborer_wage_per_step": config.laborer_wage_per_step
        }
    }

@app.post("/api/step")
async def step_simulation(count: int = Query(1, description="Number of steps to execute")):
    """Step the simulation X times."""
    if count < 1:
        raise HTTPException(status_code=400, detail="Count must be at least 1")
    
    last_result = None
    for _ in range(count):
        last_result = sim.step()
        
    return {
        "success": True,
        "steps_run": count,
        "latest_stats": last_result["stats"] if last_result else None,
        "logs": last_result["logs"] if last_result else []
    }

@app.post("/api/reset")
async def reset_simulation():
    """Reset the simulation back to initial state."""
    sim.reset()
    return {"success": True, "message": "Simulation reset successfully"}

@app.post("/api/config")
async def update_config(update: ConfigUpdate):
    """Update config settings dynamically during runtime."""
    config.tax_rate = update.tax_rate
    config.welfare_threshold_money = update.welfare_threshold_money
    config.welfare_threshold_food = update.welfare_threshold_food
    config.farmer_food_production_per_step = update.farmer_food_production_per_step
    config.laborer_wage_per_step = update.laborer_wage_per_step
    return {"success": True, "message": "Configuration updated successfully"}
