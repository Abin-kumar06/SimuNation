import React, { useRef, useEffect, useCallback, useState } from "react";

interface AgentData {
  id: number;
  x: number;
  y: number;
  profession: string;
  activity: string;
  facing: string;
  health: number;
  hunger: number;
  age_stage: string;
  carrying: string | null;
  starving: boolean;
  sleeping: boolean;
}

interface TileData {
  x: number;
  y: number;
  type: string;
  variant: number;
  building: string | null;
  agents: number;
  indicators: string[];
}

interface WorldRenderData {
  tiles: TileData[];
  agents: AgentData[];
  settlements: {
    name: string;
    x: number;
    y: number;
    population: number;
    dominant_profession: string;
    size: number;
  }[];
  trade_routes: {
    from: [number, number];
    to: [number, number];
    volume: number;
    resource: string;
  }[];
  events: {
    type: string;
    severity: string;
    message: string;
    location: [number, number];
  }[];
  time: string;
  season: string;
  timestep: number;
}

interface MapCanvasIsometricProps {
  worldData: WorldRenderData | null;
  onSelectAgent: (agent: any) => void;
  selectedAgentId: number | null;
}

const TILE_W = 64;
const TILE_H = 32;
const TILE_D = 12; // Height for building elevation

const TILE_COLORS: Record<string, string[]> = {
  farm: ["#3f6212", "#4d7c0f", "#65a30d", "#84cc16"],
  forest: ["#064e3b", "#047857", "#10b981", "#34d399"],
  river: ["#0369a1", "#0284c7", "#0ea5e9", "#38bdf8"],
  village: ["#7c2d12", "#9a3412", "#c2410c", "#ea580c"],
  town: ["#1e293b", "#334155", "#475569", "#64748b"],
  mine: ["#451a03", "#78350f", "#92400e", "#b45309"],
  mountain: ["#3f3f46", "#52525b", "#71717a", "#a1a1aa"],
};

const BUILDING_COLORS: Record<string, string> = {
  farm_plot: "#a3e635",
  house: "#fde047",
  market: "#f59e0b",
  mine_shaft: "#71717a",
};

const AGENT_COLORS: Record<string, string> = {
  farmer: "#22c55e",
  miner: "#f97316",
  builder: "#a855f7",
  doctor: "#ec4899",
  teacher: "#3b82f6",
  worker: "#f59e0b",
  trader: "#eab308",
  merchant: "#06b6d4",
  child: "#e5e7eb",
  unemployed: "#9ca3af",
};

const ACTIVITY_EMOJI: Record<string, string> = {
  farming: "🌾",
  mining: "⛏️",
  trading: "💰",
  resting: "💤",
  foraging: "🌿",
  social: "💬",
  walking: "🚶",
  idle: "👤",
  dead: "💀",
};

export const MapCanvasIsometric: React.FC<MapCanvasIsometricProps> = ({
  worldData,
  onSelectAgent,
  selectedAgentId,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Smooth camera settings stored in refs for 60fps movement
  const cameraRef = useRef({ x: 0, y: 0, zoom: 1.0 });
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const cameraStartRef = useRef({ x: 0, y: 0 });
  const animFrameRef = useRef<number>(0);

  const [hoveredAgent, setHoveredAgent] = useState<AgentData | null>(null);

  // Initialize camera position to center of map
  useEffect(() => {
    const canvas = canvasRef.current;
    if (canvas) {
      cameraRef.current.x = 0;
      cameraRef.current.y = 0;
      cameraRef.current.zoom = 1.0;
    }
  }, []);

  // Projections
  const isoToScreen = useCallback((x: number, y: number, canvasWidth: number, canvasHeight: number) => {
    const screenX = ((x - y) * TILE_W / 2) * cameraRef.current.zoom + canvasWidth / 2 + cameraRef.current.x;
    const screenY = ((x + y) * TILE_H / 2) * cameraRef.current.zoom + canvasHeight / 6 + cameraRef.current.y;
    return { x: screenX, y: screenY };
  }, []);



  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !worldData) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    // Background
    ctx.fillStyle = "#090d16";
    ctx.fillRect(0, 0, width, height);

    // 1. Draw Tiles (sorted by depth back-to-front)
    const sortedTiles = [...worldData.tiles].sort((a, b) => (a.x + a.y) - (b.x + b.y));
    const zoom = cameraRef.current.zoom;

    sortedTiles.forEach((tile) => {
      const pos = isoToScreen(tile.x, tile.y, width, height);
      
      // Client-side culling: skip rendering if tile is far outside viewport bounds
      const padding = TILE_W * zoom;
      if (
        pos.x < -padding ||
        pos.x > width + padding ||
        pos.y < -padding ||
        pos.y > height + padding
      ) {
        return;
      }

      const colors = TILE_COLORS[tile.type] || TILE_COLORS.mountain;
      const color = colors[tile.variant % colors.length];

      // Top isometric diamond face
      ctx.beginPath();
      ctx.moveTo(pos.x, pos.y - (TILE_H / 2) * zoom);
      ctx.lineTo(pos.x + (TILE_W / 2) * zoom, pos.y);
      ctx.lineTo(pos.x, pos.y + (TILE_H / 2) * zoom);
      ctx.lineTo(pos.x - (TILE_W / 2) * zoom, pos.y);
      ctx.closePath();

      ctx.fillStyle = color;
      ctx.fill();

      // Border lines
      ctx.strokeStyle = "rgba(0, 0, 0, 0.15)";
      ctx.lineWidth = 1;
      ctx.stroke();

      // Draw building if it exists
      if (tile.building) {
        const bHeight = TILE_D * zoom;
        const bColor = BUILDING_COLORS[tile.building] || "#888";

        // Roof top diamond
        ctx.beginPath();
        ctx.moveTo(pos.x, pos.y - (TILE_H / 2) * zoom - bHeight);
        ctx.lineTo(pos.x + (TILE_W / 3) * zoom, pos.y - bHeight);
        ctx.lineTo(pos.x, pos.y + (TILE_H / 3) * zoom - bHeight);
        ctx.lineTo(pos.x - (TILE_W / 3) * zoom, pos.y - bHeight);
        ctx.closePath();
        ctx.fillStyle = bColor;
        ctx.fill();

        // Left Side Face
        ctx.beginPath();
        ctx.moveTo(pos.x - (TILE_W / 3) * zoom, pos.y - bHeight);
        ctx.lineTo(pos.x, pos.y + (TILE_H / 3) * zoom - bHeight);
        ctx.lineTo(pos.x, pos.y + (TILE_H / 3) * zoom);
        ctx.lineTo(pos.x - (TILE_W / 3) * zoom, pos.y);
        ctx.closePath();
        ctx.fillStyle = "rgba(0, 0, 0, 0.25)";
        ctx.fill();

        // Right Side Face
        ctx.beginPath();
        ctx.moveTo(pos.x, pos.y + (TILE_H / 3) * zoom - bHeight);
        ctx.lineTo(pos.x + (TILE_W / 3) * zoom, pos.y - bHeight);
        ctx.lineTo(pos.x + (TILE_W / 3) * zoom, pos.y);
        ctx.lineTo(pos.x, pos.y + (TILE_H / 3) * zoom);
        ctx.closePath();
        ctx.fillStyle = "rgba(0, 0, 0, 0.1)";
        ctx.fill();
      }

      // Special resource indicator dot
      if (tile.indicators && tile.indicators.includes("growing")) {
        ctx.fillStyle = "#86efac";
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 3 * zoom, 0, Math.PI * 2);
        ctx.fill();
      }
    });

    // 2. Draw Trade Routes (animated moving gold dots)
    if (worldData.trade_routes) {
      const now = Date.now();
      worldData.trade_routes.forEach((route) => {
        const fromPos = isoToScreen(route.from[0], route.from[1], width, height);
        const toPos = isoToScreen(route.to[0], route.to[1], width, height);

        ctx.strokeStyle = "rgba(251, 191, 36, 0.35)";
        ctx.lineWidth = 1.5 * zoom;
        ctx.setLineDash([4 * zoom, 4 * zoom]);
        ctx.beginPath();
        ctx.moveTo(fromPos.x, fromPos.y);
        ctx.lineTo(toPos.x, toPos.y);
        ctx.stroke();
        ctx.setLineDash([]);

        // Animate cargo particle
        const duration = 2000;
        const t = (now % duration) / duration;
        const pX = fromPos.x + (toPos.x - fromPos.x) * t;
        const pY = fromPos.y + (toPos.y - fromPos.y) * t;

        ctx.fillStyle = "#fbbf24";
        ctx.beginPath();
        ctx.arc(pX, pY, 3 * zoom, 0, Math.PI * 2);
        ctx.fill();
      });
    }

    // 3. Draw Settlements circles
    if (worldData.settlements) {
      worldData.settlements.forEach((settlement) => {
        const pos = isoToScreen(settlement.x, settlement.y, width, height);
        
        ctx.fillStyle = "rgba(99, 102, 241, 0.12)";
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, settlement.size * 12 * zoom, 0, Math.PI * 2);
        ctx.fill();

        ctx.strokeStyle = "rgba(99, 102, 241, 0.4)";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Label
        ctx.fillStyle = "#c7d2fe";
        ctx.font = `bold ${Math.max(10, 12 * zoom)}px sans-serif`;
        ctx.textAlign = "center";
        ctx.fillText(settlement.name, pos.x, pos.y - 12 * zoom);
        
        ctx.fillStyle = "#818cf8";
        ctx.font = `${Math.max(8, 9 * zoom)}px sans-serif`;
        ctx.fillText(`Pop: ${settlement.population}`, pos.x, pos.y - 2 * zoom);
      });
    }

    // 4. Draw Events pulsing markers
    if (worldData.events) {
      const now = Date.now();
      worldData.events.forEach((event) => {
        const pos = isoToScreen(event.location[0], event.location[1], width, height);
        const pulse = (Math.sin(now / 150) + 1) / 2;

        const baseColor = event.severity === "high" ? "rgba(239, 68, 68," : "rgba(245, 158, 11,";
        ctx.fillStyle = `${baseColor} 0.15)`;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 25 * zoom, 0, Math.PI * 2);
        ctx.fill();

        ctx.strokeStyle = `${baseColor} ${0.3 + pulse * 0.7})`;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, (25 + pulse * 10) * zoom, 0, Math.PI * 2);
        ctx.stroke();
      });
    }

    // 5. Draw Agents (sorted by depth Y coordinate)
    const sortedAgents = [...worldData.agents].sort((a, b) => a.y - b.y);

    sortedAgents.forEach((agent) => {
      const pos = isoToScreen(agent.x, agent.y, width, height);
      const isSelected = selectedAgentId === agent.id;

      // Selection Highlight Ring
      if (isSelected) {
        ctx.strokeStyle = "#818cf8";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.ellipse(pos.x, pos.y, 10 * zoom, 5 * zoom, 0, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Draw shadow
      ctx.fillStyle = "rgba(0, 0, 0, 0.4)";
      ctx.beginPath();
      ctx.ellipse(pos.x, pos.y + 2, 6 * zoom, 3 * zoom, 0, 0, Math.PI * 2);
      ctx.fill();

      // Agent dot/peg body
      const size = agent.age_stage === "child" ? 5 : agent.age_stage === "elder" ? 6 : 7;
      const color = AGENT_COLORS[agent.profession] || "#ffffff";
      
      ctx.fillStyle = agent.starving ? "#ef4444" : color;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y - size * zoom, size * zoom, 0, Math.PI * 2);
      ctx.fill();

      // Activity emoji icon above head
      if (agent.activity && ACTIVITY_EMOJI[agent.activity]) {
        ctx.font = `${Math.max(10, 11 * zoom)}px sans-serif`;
        ctx.textAlign = "center";
        ctx.fillText(ACTIVITY_EMOJI[agent.activity], pos.x, pos.y - size * 2.2 * zoom);
      }

      // Carrying indicator
      if (agent.carrying) {
        ctx.fillStyle = "#fbbf24";
        ctx.beginPath();
        ctx.arc(pos.x + size * 0.9 * zoom, pos.y - size * 1.5 * zoom, 2 * zoom, 0, Math.PI * 2);
        ctx.fill();
      }

      // Health bar
      if (agent.health < 1.0) {
        const barW = 16 * zoom;
        const barH = 2 * zoom;
        ctx.fillStyle = "#1e293b";
        ctx.fillRect(pos.x - barW / 2, pos.y + 6 * zoom, barW, barH);
        
        ctx.fillStyle = agent.health > 0.5 ? "#22c55e" : agent.health > 0.25 ? "#f59e0b" : "#ef4444";
        ctx.fillRect(pos.x - barW / 2, pos.y + 6 * zoom, barW * agent.health, barH);
      }
    });

    // 6. Day/Night & Weather/Season Overlay Tint
    const timeTints: Record<string, string> = {
      morning: "rgba(251, 191, 36, 0.04)",
      day: "rgba(0, 0, 0, 0)",
      evening: "rgba(139, 92, 246, 0.08)",
      night: "rgba(15, 23, 42, 0.35)",
    };

    const tint = timeTints[worldData.time];
    if (tint) {
      ctx.fillStyle = tint;
      ctx.fillRect(0, 0, width, height);
    }

    // Schedule next animation loop frame
    animFrameRef.current = requestAnimationFrame(render);
  }, [worldData, selectedAgentId, isoToScreen]);

  // Handle Resize
  const handleResize = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    canvas.width = container.clientWidth;
    canvas.height = 500; // Constrain visualizer height
  }, []);

  useEffect(() => {
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [handleResize]);

  // Request frames when visual state updates
  useEffect(() => {
    animFrameRef.current = requestAnimationFrame(render);
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [render]);

  // Interaction handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    isDraggingRef.current = true;
    dragStartRef.current = { x: e.clientX, y: e.clientY };
    cameraStartRef.current = { ...cameraRef.current };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas || !worldData) return;

    const width = canvas.width;
    const height = canvas.height;

    if (isDraggingRef.current) {
      cameraRef.current.x = cameraStartRef.current.x + (e.clientX - dragStartRef.current.x);
      cameraRef.current.y = cameraStartRef.current.y + (e.clientY - dragStartRef.current.y);
    }

    // Hover state detection
    const rect = canvas.getBoundingClientRect();
    const sX = e.clientX - rect.left;
    const sY = e.clientY - rect.top;

    const zoom = cameraRef.current.zoom;
    const hovered = worldData.agents.find((agent) => {
      const pos = isoToScreen(agent.x, agent.y, width, height);
      const dist = Math.hypot(pos.x - sX, pos.y - sY - 5 * zoom);
      return dist < 12 * zoom;
    });

    if (hovered) {
      setHoveredAgent(hovered);
    } else {
      setHoveredAgent(null);
    }
  };

  const handleMouseUp = () => {
    isDraggingRef.current = false;
  };

  const handleCanvasClick = (e: React.MouseEvent) => {
    const canvas = canvasRef.current;
    if (!canvas || !worldData) return;

    const width = canvas.width;
    const height = canvas.height;

    const rect = canvas.getBoundingClientRect();
    const sX = e.clientX - rect.left;
    const sY = e.clientY - rect.top;

    const zoom = cameraRef.current.zoom;
    const clickedAgent = worldData.agents.find((agent) => {
      const pos = isoToScreen(agent.x, agent.y, width, height);
      const dist = Math.hypot(pos.x - sX, pos.y - sY - 5 * zoom);
      return dist < 12 * zoom;
    });

    if (clickedAgent) {
      onSelectAgent(clickedAgent);
    } else {
      onSelectAgent(null);
    }
  };

  const handleWheel = (e: React.WheelEvent) => {
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    cameraRef.current.zoom *= zoomFactor;
    cameraRef.current.zoom = Math.max(0.3, Math.min(3.0, cameraRef.current.zoom));
  };

  return (
    <div ref={containerRef} className="relative border border-slate-700/80 rounded-xl overflow-hidden shadow-2xl bg-slate-950 select-none">
      {/* HUD Info Controls overlay */}
      <div className="absolute top-4 right-4 z-10 bg-slate-900/90 border border-slate-700/60 p-3 rounded-lg backdrop-blur-md text-[11px] text-slate-300 pointer-events-none">
        <h4 className="font-bold text-slate-100 mb-1">Controls</h4>
        <p>🖱️ Drag: Pan Camera</p>
        <p>⚙️ Scroll: Zoom Viewport</p>
        <p>👤 Click Character: View Details</p>
      </div>

      {hoveredAgent && (
        <div className="absolute top-4 left-4 z-10 bg-slate-900/95 border border-slate-700 p-3 rounded-lg shadow-xl text-xs text-white pointer-events-none min-w-[180px]">
          <div className="font-bold text-indigo-400">Agent #{hoveredAgent.id}</div>
          <div className="text-slate-400 capitalize">{hoveredAgent.profession} | {hoveredAgent.age_stage}</div>
          <div className="mt-1 flex justify-between">
            <span>Health:</span> <span className="font-semibold text-emerald-400">{(hoveredAgent.health * 100).toFixed(0)}%</span>
          </div>
          <div className="flex justify-between">
            <span>Hunger:</span> <span className="font-semibold text-amber-400">{(hoveredAgent.hunger * 100).toFixed(0)}%</span>
          </div>
          <div className="text-[10px] text-indigo-300 mt-1 border-t border-slate-700/50 pt-1 capitalize">
            Activity: {hoveredAgent.activity}
          </div>
        </div>
      )}

      <canvas
        ref={canvasRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onClick={handleCanvasClick}
        onWheel={handleWheel}
        className="w-full block cursor-grab active:cursor-grabbing"
      />
    </div>
  );
};
