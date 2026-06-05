# SimuNation V2 — Advanced Emergent AI Civilization Simulator

SimuNation V2 is a multi-agent simulation modeling an emergent autonomous society on a 100x100 tile-based geographic grid. All behaviors (economic trades, social trust, marriages, childbirths, and crime) emerge naturally from agent attributes and local conditions without hardcoded outcomes.

---

## 🧬 Core Architectures

### 1. Geographic Map Grid (`backend/app/simunation/world.py`)
- **100x100 Tile Matrix** with types: `Farm`, `Forest`, `River`, `Village`, `Town`, `Mine`, and `Mountain`.
- Tile positions influence production efficiency and travel destinations.

### 2. Advanced AI Agent Mind (`backend/app/simunation/agent.py`)
- **Traits**: `greed`, `cooperation`, `riskTolerance`, `intelligence`, `ambition`.
- **States**: Age, Money, Food, Health, Energy, Happiness, Housing Level.
- **Professions**:
  - *Farmers*: harvest food.
  - *Miners*: extract raw materials.
  - *Builders*: upgrade housing levels.
  - *Doctors*: heal injured/unwell agents.
  - *Teachers*: elevate community intelligence.
  - *Workers*: support general labor.
  - *Traders/Merchants*: arbitrate resources between villages and towns.
- **Emergent Crime**: Under extreme hunger or poverty, greedy agents may rob nearby neighbors, resulting in severe trust damage.

### 3. Social Engine & Lifecycles (`backend/app/simunation/relationships.py` & `families.py`)
- **Social Trust**: Trust modifies based on deals, gifts, or betrayals. Agents select trading partners based on high trust.
- **Demographics**: Adults with savings form partnerships, marry, and birth children. Children grow up and roll random adult professions.

### 4. Dynamic Government Entity (`backend/app/simunation/government.py`)
- Taxes money reserves and redistributes welfare to citizens facing starvation.
- Adaptively adjusts policy: lowers tax rates and raises welfare payouts during starvation spikes.

---

## 🚀 Quick Start Instructions

To start SimuNation V2:

### 1. Launch Backend API
In your terminal, navigate to the `backend/` folder and run the server script:
```bash
cd backend
pip install -r requirements.txt
python run.py
```
*FastAPI server runs on **`http://127.0.0.1:8000`***

### 2. Launch Frontend Dev Server
Open a second terminal, navigate to the `frontend/` folder, and launch the Vite client:
```bash
cd frontend
npm install
npm run dev
```
*Vite dev server opens on **`http://127.0.0.1:5173`*** (or browse to local link shown).

---

## 🧪 Unit Tests
Run backend test coverage:
```bash
python -m pytest backend/tests/
```
