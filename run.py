import argparse
import uvicorn
import time
from simunation.simulation import Simulation

def run_cli(steps: int):
    print("=" * 60)
    print("SimuNation — Emergent AI Civilization Simulator (CLI)")
    print("=" * 60)
    
    sim = Simulation()
    print(f"Population: {len(sim.world.agents)} agents initialized.")
    print("Starting simulation loop...")
    
    for _ in range(steps):
        res = sim.step()
        stats = res["stats"]
        
        # Print logs from this timestep
        for log in res["logs"]:
            print(log)
            
        print(f"Stats: Timestep {stats['timestep']} | Pop: {stats['population_alive']} alive, {stats['population_starving']} starving, {stats['population_dead']} dead | Avg Food Price: ${stats['average_food_price']:.2f} | Gini: {stats['gini_coefficient']:.3f}")
        print("-" * 60)
        time.sleep(0.3)
        
    print("Simulation completed.")
    print(f"Final Wealth Gini Index: {sim.world.calculate_gini():.3f}")

def run_web():
    print("Starting SimuNation FastAPI web dashboard...")
    uvicorn.run("simunation.app:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the SimuNation Emergent Civilization Simulator.")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode instead of starting the web server")
    parser.add_argument("--steps", type=int, default=50, help="Number of steps to run in CLI mode")
    
    args = parser.parse_args()
    
    if args.cli:
        run_cli(args.steps)
    else:
        run_web()
