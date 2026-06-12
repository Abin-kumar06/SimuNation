import { useState, useEffect, useRef } from "react";
import { MapCanvas } from "./components/MapCanvas";
import { MapCanvas3D } from "./components/MapCanvas3D";
import { StatsDashboard } from "./components/StatsDashboard";
import { ControlPanel } from "./components/ControlPanel";

interface AgentData {
  id: number;
  name: string;
  role: string;
  age: number;
  money: number;
  food: number;
  health: number;
  energy: number;
  happiness: number;
  housing: string;
  x: number;
  y: number;
  is_alive: boolean;
  starving: boolean;
  last_action: string;
  children_count: number;
}

const BACKEND_URL = "http://127.0.0.1:8000";

function App() {
  const [grid, setGrid] = useState<string[][]>([]);
  const [agents, setAgents] = useState<AgentData[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [logs, setLogs] = useState<string[]>([]);
  const [stats, setStats] = useState<any>({});
  const [government, setGovernment] = useState<any>({});
  const [selectedAgent, setSelectedAgent] = useState<AgentData | null>(null);
  const [isAutoplay, setIsAutoplay] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<"2D" | "3D">("3D");
  const selectedAgentRef = useRef<AgentData | null>(null);
  const [selectedAgentMonologue, setSelectedAgentMonologue] = useState<string>("");
  const [selectedAgentMemories, setSelectedAgentMemories] = useState<string[]>([]);

  useEffect(() => {
    selectedAgentRef.current = selectedAgent;
    
    // Fetch monologue and memories when selection changes
    if (selectedAgent) {
      fetch(`${BACKEND_URL}/api/agent/${selectedAgent.id}/monologue`)
        .then((res) => res.json())
        .then((data) => {
          setSelectedAgentMonologue(data.monologue);
          setSelectedAgentMemories(data.memories);
        })
        .catch((err) => console.error("Error fetching agent monologue/memories:", err));
    } else {
      setSelectedAgentMonologue("");
      setSelectedAgentMemories([]);
    }
  }, [selectedAgent?.id]);

  useEffect(() => {
    // 1. Fetch map static layout once
    fetch(`${BACKEND_URL}/api/map`)
      .then((res) => res.json())
      .then((data) => setGrid(data.grid))
      .catch((err) => console.error("Error fetching map:", err));

    // 2. Fetch initial state
    fetchState();

    // 3. Establish WebSocket connection
    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;

    const connectWS = () => {
      const wsUrl = `ws://127.0.0.1:8000/api/ws`;
      console.log("Connecting to WebSocket:", wsUrl);
      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "state") {
            const data = msg.data;
            setAgents(data.agents);
            setHistory(data.history);
            setLogs(data.logs);
            setStats(data.stats);
            setGovernment(data.government);
            
            // Sync selected agent
            if (selectedAgentRef.current) {
              const updated = data.agents.find((a: AgentData) => a.id === selectedAgentRef.current!.id);
              setSelectedAgent(updated || null);
            }
          }
        } catch (err) {
          console.error("Error parsing WS message:", err);
        }
      };

      ws.onclose = () => {
        console.warn("WebSocket disconnected. Retrying in 3 seconds...");
        reconnectTimeout = setTimeout(connectWS, 3000);
      };

      ws.onerror = (err) => {
        console.error("WebSocket error, closing:", err);
        ws?.close();
      };
    };

    connectWS();

    return () => {
      if (ws) {
        ws.onclose = null; // Prevent reconnect loop
        ws.close();
      }
      clearTimeout(reconnectTimeout);
    };
  }, []);

  // Poll step if autoplay is on (triggers backend, which broadcasts updates)
  useEffect(() => {
    let interval: any = null;
    if (isAutoplay) {
      interval = setInterval(() => {
        handleStep(1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [isAutoplay]);

  const fetchState = () => {
    fetch(`${BACKEND_URL}/api/state`)
      .then((res) => res.json())
      .then((data) => {
        setAgents(data.agents);
        setHistory(data.history);
        setLogs(data.logs);
        setStats(data.stats);
        setGovernment(data.government);

        // Sync selected agent
        if (selectedAgentRef.current) {
          const updated = data.agents.find((a: AgentData) => a.id === selectedAgentRef.current!.id);
          setSelectedAgent(updated || null);
        }
      })
      .catch((err) => console.error("Error fetching state:", err));
  };

  const handleStep = (count: number) => {
    fetch(`${BACKEND_URL}/api/step?count=${count}`, { method: "POST" })
      .catch((err) => console.error("Error stepping:", err));
  };

  const handleReset = () => {
    if (confirm("Are you sure you want to reset civilization?")) {
      fetch(`${BACKEND_URL}/api/reset`, { method: "POST" })
        .then(() => {
          setSelectedAgent(null);
          setIsAutoplay(false);
        })
        .catch((err) => console.error("Error resetting:", err));
    }
  };

  const handleApplyPolicy = (updatedPolicy: any) => {
    fetch(`${BACKEND_URL}/api/policy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updatedPolicy)
    })
      .catch((err) => console.error("Error applying policy:", err));
  };

  const handleTriggerEvent = (eventName: string) => {
    fetch(`${BACKEND_URL}/api/trigger-event?name=${encodeURIComponent(eventName)}`, { method: "POST" })
      .then(() => fetchState())
      .catch((err) => console.error("Error triggering event:", err));
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-600 selection:text-white">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur-md px-6 py-4 flex justify-between items-center sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center font-bold text-lg text-white shadow-lg shadow-indigo-600/30">
            S2
          </div>
          <div>
            <h1 className="font-semibold text-lg leading-tight tracking-tight text-white">SimuNation V2</h1>
            <span className="text-slate-500 text-xs font-semibold">Emergent AI Civilization Upgraded Simulator</span>
          </div>
        </div>

        {/* Global Summary Stats */}
        <div className="flex gap-6 items-center">
          <div className="text-right">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">Timestep</span>
            <span className="text-lg font-bold text-indigo-400">{stats.timestep || 0}</span>
          </div>
          <div className="text-right">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">Alive</span>
            <span className="text-lg font-bold text-emerald-400">{stats.population_alive || 0}</span>
          </div>
          <div className="text-right">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">Starving</span>
            <span className="text-lg font-bold text-orange-400">{stats.population_starving || 0}</span>
          </div>
          <div className="text-right">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-semibold">Active Events</span>
            <span className="text-xs font-semibold px-2 py-0.5 bg-rose-950 text-rose-400 border border-rose-800 rounded-md block mt-0.5">
              {stats.active_events && stats.active_events.length > 0 ? stats.active_events.join(", ") : "None"}
            </span>
          </div>
        </div>
      </header>

      {/* Main Grid */}
      <main className="max-w-[1600px] w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-4 gap-6 flex-1">
        {/* Left Control Column */}
        <div className="lg:col-span-1 flex flex-col gap-6">
          {government.tax_rate !== undefined && (
            <ControlPanel
              policy={{
                tax_rate: government.tax_rate,
                welfare_amount: government.welfare_amount,
                welfare_money_threshold: government.welfare_money_threshold,
                welfare_food_threshold: government.welfare_food_threshold
              }}
              onStep={handleStep}
              onReset={handleReset}
              onApplyPolicy={handleApplyPolicy}
              onTriggerEvent={handleTriggerEvent}
              isAutoplay={isAutoplay}
              onToggleAutoplay={() => setIsAutoplay(!isAutoplay)}
            />
          )}

          {/* Selected Agent Inspector */}
          {selectedAgent && (
            <div className="bg-slate-900 border border-indigo-500/25 rounded-xl p-5 shadow-2xl relative overflow-hidden">
              <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-600/5 rounded-full blur-2xl pointer-events-none" />
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h4 className="font-semibold text-slate-100">{selectedAgent.name}</h4>
                  <span className="text-indigo-400 text-xs font-semibold uppercase tracking-wider">{selectedAgent.role}</span>
                </div>
                <button
                  onClick={() => setSelectedAgent(null)}
                  className="text-slate-500 hover:text-slate-300 font-bold text-xs"
                >
                  ✕
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                  <span className="text-slate-500 block">ID / Age</span>
                  <span className="font-bold">#{selectedAgent.id} / {selectedAgent.age} yrs</span>
                </div>
                <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                  <span className="text-slate-500 block">Status</span>
                  <span className={`font-bold ${selectedAgent.is_alive ? "text-emerald-400" : "text-rose-500"}`}>
                    {selectedAgent.is_alive ? (selectedAgent.starving ? "Starving" : "Alive") : "Deceased"}
                  </span>
                </div>
                <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                  <span className="text-slate-500 block">Money</span>
                  <span className="font-bold text-emerald-400">${selectedAgent.money}</span>
                </div>
                <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                  <span className="text-slate-500 block">Food Stock</span>
                  <span className="font-bold text-amber-400">{selectedAgent.food} units</span>
                </div>
                <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                  <span className="text-slate-500 block">Health</span>
                  <span className="font-bold">{selectedAgent.health}/100</span>
                </div>
                <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                  <span className="text-slate-500 block">Happiness</span>
                  <span className="font-bold">{selectedAgent.happiness}/100</span>
                </div>
                <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                  <span className="text-slate-500 block">Housing</span>
                  <span className="font-bold">{selectedAgent.housing}</span>
                </div>
                <div className="bg-slate-950 p-2 rounded-lg border border-slate-800">
                  <span className="text-slate-500 block">Children</span>
                  <span className="font-bold">{selectedAgent.children_count}</span>
                </div>
                <div className="col-span-2 bg-slate-950 p-2 rounded-lg border border-slate-800">
                  <span className="text-slate-500 block">Last Intention</span>
                  <span className="italic text-slate-300 font-medium">"{selectedAgent.last_action}"</span>
                </div>

                {/* Monologue */}
                {selectedAgentMonologue && (
                  <div className="col-span-2 bg-indigo-955/25 border border-indigo-500/20 p-3 rounded-lg text-xs leading-relaxed text-indigo-200">
                    <span className="text-indigo-400 font-bold block text-[10px] uppercase tracking-wider mb-1">Inner Monologue</span>
                    "{selectedAgentMonologue}"
                  </div>
                )}

                {/* Memories */}
                {selectedAgentMemories.length > 0 && (
                  <div className="col-span-2 bg-slate-955 p-3 rounded-lg border border-slate-800 flex flex-col gap-1.5 max-h-48 overflow-y-auto scrollbar-thin">
                    <span className="text-slate-400 font-bold text-[10px] uppercase tracking-wider block border-b border-slate-800 pb-1 mb-1">Historical Memories</span>
                    {selectedAgentMemories.map((m, idx) => (
                      <div key={idx} className="text-[11px] text-slate-300 leading-tight">
                        • {m}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Center / Right Visual Area */}
        <div className="lg:col-span-3 flex flex-col gap-6">
          {/* Tile Grid map */}
          {grid.length > 0 && (
            <div className="flex flex-col gap-4">
              <div className="flex justify-between items-center bg-slate-900 border border-slate-800/80 px-5 py-3 rounded-xl shadow-xl">
                <div className="flex items-center gap-2">
                  <span className="text-slate-200 font-semibold text-sm tracking-wide">🌍 World Map Visualization</span>
                  <span className="text-[10px] bg-indigo-950 text-indigo-400 border border-indigo-900/60 px-2 py-0.5 rounded font-bold uppercase tracking-wider">
                    {viewMode} Mode Active
                  </span>
                </div>
                <div className="bg-slate-950 p-0.5 rounded-lg border border-slate-800 flex gap-1 text-xs">
                  <button
                    onClick={() => setViewMode("2D")}
                    className={`px-3.5 py-1.5 rounded-md transition-all font-semibold cursor-pointer ${
                      viewMode === "2D"
                        ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    2D Grid
                  </button>
                  <button
                    onClick={() => setViewMode("3D")}
                    className={`px-3.5 py-1.5 rounded-md transition-all font-semibold cursor-pointer ${
                      viewMode === "3D"
                        ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    3D Town
                  </button>
                </div>
              </div>

              {viewMode === "2D" ? (
                <MapCanvas
                  grid={grid}
                  agents={agents}
                  selectedAgentId={selectedAgent?.id || null}
                  onSelectAgent={setSelectedAgent}
                />
              ) : (
                <MapCanvas3D
                  grid={grid}
                  agents={agents}
                  selectedAgentId={selectedAgent?.id || null}
                  onSelectAgent={setSelectedAgent}
                />
              )}
            </div>
          )}

          {/* Stats Graphs charts */}
          <StatsDashboard history={history} />

          {/* Logs Terminal */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl flex flex-col gap-3">
            <h3 className="font-semibold text-slate-200 flex items-center gap-2">
              📜 Civilization Event Logs
            </h3>
            <div className="h-44 bg-slate-950 rounded-lg p-3 overflow-y-auto font-mono text-xs border border-slate-800 flex flex-col gap-1.5 scrollbar-thin">
              {logs.map((log, idx) => {
                let colorClass = "text-slate-400";
                if (log.startsWith("---")) colorClass = "text-slate-200 font-bold border-t border-slate-800/40 pt-1.5 mt-1";
                else if (log.includes("Robbed") || log.includes(" rob ") || log.includes("Crime")) colorClass = "text-rose-400 font-medium";
                else if (log.includes("Event Ended") || log.includes("Ended")) colorClass = "text-emerald-400";
                else if (log.includes("Event Alert") || log.includes("Drought") || log.includes("Disease")) colorClass = "text-amber-500 font-medium";
                else if (log.includes("Marriage") || log.includes("Birth")) colorClass = "text-pink-400";
                else if (log.includes("Govt")) colorClass = "text-cyan-400";
                else if (log.includes("bought")) colorClass = "text-slate-300";

                return (
                  <div key={idx} className={`${colorClass} leading-relaxed`}>
                    {log}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
