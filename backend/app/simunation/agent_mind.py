import os
import random
from typing import List, Dict, Any, Optional, TypedDict
import numpy as np
import google.generativeai as genai
from simunation.database import add_agent_memory, get_agent_memories, retrieve_relevant_memories

# Setup Gemini API client
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    HAS_GEMINI = True
else:
    HAS_GEMINI = False
    print("⚠️ Warning: GEMINI_API_KEY environment variable not set. Running in simulation/mock mode for LLM generation.")

def get_embedding(text: str) -> List[float]:
    """Generates a text embedding vector (768 dimensions) using Gemini or mock fallback."""
    if HAS_GEMINI:
        try:
            res = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return res["embedding"]
        except Exception as e:
            print(f"Error fetching embedding from Gemini: {e}")
            
    # Mock embedding: deterministic float list based on word hash
    vector = []
    seed = sum(ord(c) for c in text)
    random.seed(seed)
    for _ in range(768):
        vector.append(random.uniform(-1, 1))
    return vector

def generate_agent_inner_monologue(agent_data: Dict[str, Any]) -> str:
    """Generates a short first-person inner monologue for an agent based on traits, state, and recalled memories."""
    # 1. Retrieve relevant memories from SQLite
    memories = get_agent_memories(agent_data["id"])
    mem_context = ""
    if memories:
        # Get top 3 most recent memories
        recent = [m["memory_text"] for m in memories[:3]]
        mem_context = "Recent Memories:\n- " + "\n- ".join(recent)
        
    traits = f"Greed: {agent_data.get('greed', 50):.0f}%, Cooperation: {agent_data.get('cooperation', 50):.0f}%, Risk: {agent_data.get('riskTolerance', 50):.0f}%"
    state = f"Age: {agent_data['age']}, Money: ${agent_data['money']}, Food: {agent_data['food']}, Health: {agent_data['health']}, Happiness: {agent_data['happiness']}"
    
    prompt = f"""
You are {agent_data['name']}, a {agent_data['role']} in a simulated civilization grid.
Your current attributes:
{traits}
{state}
Recent Action: {agent_data.get('last_action', 'None')}
{mem_context}

Write a short first-person inner monologue (exactly 1 or 2 sentences) expressing your thoughts, desires, worries, or plans. Do not include quotes around your response.
"""
    
    if HAS_GEMINI:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return response.text.strip().replace('"', '')
        except Exception as e:
            print(f"Error generating monologue from Gemini: {e}")

    # High-fidelity mock fallback
    worries = []
    if agent_data["food"] < 3.0:
        worries.append("I am so hungry, my stomach is growling.")
    if agent_data["money"] < 15.0:
        worries.append("I'm running out of money, I need to sell something soon.")
    if agent_data["health"] < 60.0:
        worries.append("I feel weak, I might need to buy some medical treatment.")
    if agent_data["happiness"] > 80.0:
        worries.append("Life in the village is going wonderfully right now!")
        
    if agent_data["role"] == "Farmer":
        worries.append("Hope the harvest is plentiful this time.")
    elif agent_data["role"] == "Miner":
        worries.append("Must keep digging for valuable raw materials.")
    elif agent_data["role"] == "Builder":
        worries.append("There is always more housing to construct.")

    if not worries:
        worries.append("Just going about my daily business in the village.")

    random.seed(agent_data["id"] + agent_data["age"])
    return " ".join(random.sample(worries, min(2, len(worries))))

# --- LangGraph Agent Engine: Government Council Workflow ---
from langgraph.graph import StateGraph, END

class CouncilState(TypedDict):
    timestep: int
    population_alive: int
    population_starving: int
    gini_coefficient: float
    average_food_price: float
    recent_logs: List[str]
    tax_rate: float
    welfare_amount: float
    council_analysis: str
    recommended_policy: Dict[str, float]
    recommended_event: Optional[str]

def analyze_economy(state: CouncilState) -> Dict[str, Any]:
    """LangGraph node: Analyzes the village economy."""
    summary = f"""
    Timestep: {state['timestep']}
    Alive: {state['population_alive']}
    Starving: {state['population_starving']}
    Gini Index: {state['gini_coefficient']:.3f}
    Avg Food Price: ${state['average_food_price']:.2f}
    Recent Logs: {state['recent_logs'][-5:]}
    """
    
    analysis = "The village economy is stable."
    if state['population_starving'] > 5:
        analysis = "WARNING: Critical starvation outbreak! Citizen survival is at risk."
    elif state['gini_coefficient'] > 0.45:
        analysis = "CRITICAL: High wealth inequality detected! The rich are getting richer, and the poor are starving."

    return {"council_analysis": analysis}

def adjust_policy(state: CouncilState) -> Dict[str, Any]:
    """LangGraph node: Recommends fiscal policy adjustments."""
    analysis = state["council_analysis"]
    new_tax = state["tax_rate"]
    new_welfare = state["welfare_amount"]

    if "starvation" in analysis.lower():
        # Lower tax, increase welfare
        new_tax = max(0.02, state["tax_rate"] - 0.01)
        new_welfare = min(50.0, state["welfare_amount"] + 3.0)
    elif "inequality" in analysis.lower():
        # Raise tax to redistribute, raise welfare
        new_tax = min(0.15, state["tax_rate"] + 0.01)
        new_welfare = min(40.0, state["welfare_amount"] + 2.0)
    else:
        # Normal economic drift
        if state["tax_rate"] > 0.05:
            new_tax = max(0.05, state["tax_rate"] - 0.005)

    return {"recommended_policy": {"tax_rate": round(new_tax, 3), "welfare_amount": round(new_welfare, 2)}}

def trigger_event(state: CouncilState) -> Dict[str, Any]:
    """LangGraph node: Proposes dynamic world events."""
    event = None
    # 5% chance of council triggering a support/stimulus event or disaster
    if state['population_starving'] > 8:
        event = "Drought" if random.random() < 0.3 else None
    elif state['gini_coefficient'] < 0.25 and random.random() < 0.15:
        event = "Economic Boom"
    
    return {"recommended_event": event}

# Compile the LangGraph
workflow = StateGraph(CouncilState)
workflow.add_node("analyze_economy", analyze_economy)
workflow.add_node("adjust_policy", adjust_policy)
workflow.add_node("trigger_event", trigger_event)

workflow.set_entry_point("analyze_economy")
workflow.add_edge("analyze_economy", "adjust_policy")
workflow.add_edge("adjust_policy", "trigger_event")
workflow.add_edge("trigger_event", END)

council_agent = workflow.compile()

def run_government_council(sim_state: Dict[str, Any], recent_logs: List[str]) -> Dict[str, Any]:
    """Runs the LangGraph Council Agent to inspect the village state and return fiscal/event modifications."""
    stats = sim_state.get("stats", {})
    gov = sim_state.get("government", {})
    
    inputs: CouncilState = {
        "timestep": stats.get("timestep", 0),
        "population_alive": stats.get("population_alive", 0),
        "population_starving": stats.get("population_starving", 0),
        "gini_coefficient": stats.get("gini_coefficient", 0.0),
        "average_food_price": stats.get("average_food_price", 10.0),
        "recent_logs": recent_logs,
        "tax_rate": gov.get("tax_rate", 0.05),
        "welfare_amount": gov.get("welfare_amount", 15.0),
        "council_analysis": "",
        "recommended_policy": {},
        "recommended_event": None
    }
    
    try:
        result = council_agent.invoke(inputs)
        return {
            "analysis": result["council_analysis"],
            "policy": result["recommended_policy"],
            "event": result["recommended_event"]
        }
    except Exception as e:
        print(f"Error executing LangGraph council workflow: {e}")
        return {
            "analysis": "Static run",
            "policy": {"tax_rate": gov.get("tax_rate", 0.05), "welfare_amount": gov.get("welfare_amount", 15.0)},
            "event": None
        }
