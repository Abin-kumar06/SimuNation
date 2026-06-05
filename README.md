# SimuNation — Emergent AI Civilization Simulator

SimuNation is a multi-agent simulation system mimicking a small autonomous civilization. Agents behave with human-like economic goals, interacting dynamically in a virtual world where economic indicators (like prices, supply shortages, and wealth inequality) emerge organically rather than from hardcoded outcomes.

---

## 🧠 Core Architecture

The simulation is split into modular components:

1. **Agent System (`simunation/agent.py`)**
   Autonomous agents with:
   - **Unique Roles**:
     - *Farmers*: Produce food, require money.
     - *Laborers*: Earn wages working in external systems, require food to survive.
     - *Merchants*: Mediate trades by buying food low and selling it high.
   - **Personalities**:
     - *Cooperative*: Sets fair/average prices, helps stabilize the market.
     - *Selfish*: Aggressively seeks profit, marks up prices when demand is high.
     - *Risk-Taking*: Prices food with higher volatility, willing to take risks.
   - **Dynamic Memory**: Tracks moving averages of successful and failed transaction prices to adapt prices over time.

2. **Economic Engine (`simunation/economy.py`)**
   Uses a **Double-Auction Matching System**. Agents submit limit orders (Bids to buy and Asks to sell). The economy matches orders:
   - Highest bids match with lowest asks.
   - The transaction price is set to the midpoint of the bid and ask price.
   - Prices fluctuate organically based on the supply of food and cash reserves.

3. **World Engine & Government Policy (`simunation/world.py`)**
   Updates parameters per timestep:
   - **Taxation**: Collects a dynamic tax rate (default 5%) of each living agent's cash.
   - **Welfare Redistribution**: Fully redistributes collected taxes to poor/starving agents, enabling them to purchase food and survive shortages.
   - **Analytics**: Calculates total food, money, role counts, and the **Gini Inequality Coefficient**.

4. **Web UI & Server (`simunation/app.py`, `simunation/templates/index.html`)**
   FastAPI web server serving a dark-themed, glassmorphic visual dashboard displaying:
   - Real-time Chart.js graphs tracking Gini coefficient, food prices, and supply levels.
   - A live grid of all agents showing role icons, food, money, status, and interactive tooltips showing their current choices.
   - Live system events and transaction history.

---

## 🚀 Getting Started

### 📋 Prerequisites
Make sure Python (3.8+) is installed. Install package dependencies:
```bash
pip install -r requirements.txt
```

### 💻 Run Options

#### Option A: Web Server & Interactive Dashboard (Recommended)
Launch the FastAPI development server:
```bash
python run.py
```
Open your browser and navigate to **`http://127.0.0.1:8000`** to access the dashboard.

#### Option B: Terminal CLI Mode
To run a quick simulation run directly in the command prompt:
```bash
python run.py --cli --steps 50
```

---

## 📊 Running Tests
Run the test suite to verify the code logic:
```bash
python -m pytest tests/
```

---

## 🎭 Emergent Properties to Observe
- **Wealth Concentration**: If taxes and welfare are set to 0%, the Gini coefficient steadily rises as merchants and lucky farmers capture a large share of the money supply.
- **Shortage Panic**: If food supply drops, starving Laborers panic, bidding extremely high prices to secure food.
- **Welfare Stabilization**: Applying a 5-10% tax rate acts as an automatic stabilizer, preventing wealth concentration and reducing starvation-related deaths.
