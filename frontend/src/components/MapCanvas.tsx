import React, { useRef, useEffect, useState } from "react";

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

interface MapCanvasProps {
  grid: string[][];
  agents: AgentData[];
  selectedAgentId: number | null;
  onSelectAgent: (agent: AgentData | null) => void;
}

const TILE_COLORS: Record<string, string> = {
  Farm: "#15803d",
  Forest: "#064e3b",
  River: "#2563eb",
  Village: "#a16207",
  Town: "#4b5563",
  Mine: "#92400e",
  Mountain: "#1f2937",
};

const ROLE_COLORS: Record<string, string> = {
  Farmer: "#22c55e",
  Miner: "#f97316",
  Builder: "#a855f7",
  Doctor: "#ec4899",
  Teacher: "#3b82f6",
  Worker: "#f59e0b",
  Trader: "#eab308",
  Merchant: "#06b6d4",
  Child: "#e5e7eb",
};

export const MapCanvas: React.FC<MapCanvasProps> = ({ grid, agents, selectedAgentId, onSelectAgent }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [zoom, setZoom] = useState<number>(0.8);
  const [offsetX, setOffsetX] = useState<number>(0);
  const [offsetY, setOffsetY] = useState<number>(0);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const tilePixelSize = 10;
  const gridWidth = grid[0]?.length || 100;
  const gridHeight = grid.length || 100;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Clear and fill dark
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.save();
    // Apply pan and zoom transforms
    ctx.translate(offsetX, offsetY);
    ctx.scale(zoom, zoom);

    // 1. Draw Map Tiles
    for (let y = 0; y < gridHeight; y++) {
      for (let x = 0; x < gridWidth; x++) {
        const type = grid[y][x];
        ctx.fillStyle = TILE_COLORS[type] || "#1e293b";
        ctx.fillRect(x * tilePixelSize, y * tilePixelSize, tilePixelSize - 0.5, tilePixelSize - 0.5);
      }
    }

    // 2. Draw Agents
    agents.forEach((agent) => {
      if (!agent.is_alive) {
        // Draw dead symbol
        ctx.fillStyle = "#ef4444";
        ctx.font = "8px sans-serif";
        ctx.fillText("💀", agent.x * tilePixelSize - 1, agent.y * tilePixelSize + 7);
        return;
      }

      const cx = agent.x * tilePixelSize + tilePixelSize / 2;
      const cy = agent.y * tilePixelSize + tilePixelSize / 2;

      // Draw dynamic starvation alert ring
      if (agent.starving) {
        ctx.beginPath();
        ctx.arc(cx, cy, 6, 0, 2 * Math.PI);
        ctx.strokeStyle = "#f97316";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }

      // Selected agent marker
      if (agent.id === selectedAgentId) {
        ctx.beginPath();
        ctx.arc(cx, cy, 8, 0, 2 * Math.PI);
        ctx.strokeStyle = "#6366f1";
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      ctx.beginPath();
      ctx.arc(cx, cy, 3.5, 0, 2 * Math.PI);
      ctx.fillStyle = ROLE_COLORS[agent.role] || "#e5e7eb";
      ctx.fill();
    });

    ctx.restore();
  }, [grid, agents, zoom, offsetX, offsetY, selectedAgentId]);

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - offsetX, y: e.clientY - offsetY });
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDragging) return;
    setOffsetX(e.clientX - dragStart.x);
    setOffsetY(e.clientY - dragStart.y);
  };

  const handleMouseUpOrLeave = () => {
    setIsDragging(false);
  };

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    
    // Compute coordinates relative to the translation and scale transforms
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;
    
    const worldX = (clickX - offsetX) / zoom;
    const worldY = (clickY - offsetY) / zoom;
    
    const gridX = Math.floor(worldX / tilePixelSize);
    const gridY = Math.floor(worldY / tilePixelSize);

    // Find agent on this tile
    const clickedAgent = agents.find((a) => a.x === gridX && a.y === gridY && a.is_alive);
    
    if (clickedAgent) {
      onSelectAgent(clickedAgent);
    } else {
      // Find closest if click slightly off
      const nearbyAgent = agents.find((a) => Math.abs(a.x - gridX) <= 1 && Math.abs(a.y - gridY) <= 1 && a.is_alive);
      if (nearbyAgent) {
        onSelectAgent(nearbyAgent);
      } else {
        onSelectAgent(null);
      }
    }
  };

  const handleZoom = (factor: number) => {
    setZoom((prev) => Math.max(0.2, Math.min(3, prev * factor)));
  };

  return (
    <div className="relative border border-slate-700/80 rounded-xl overflow-hidden shadow-2xl bg-slate-900">
      <div className="absolute top-4 left-4 z-10 flex gap-2">
        <button
          onClick={() => handleZoom(1.2)}
          className="w-10 h-10 flex items-center justify-center bg-slate-800/85 hover:bg-slate-700 text-white rounded-lg border border-slate-700 font-bold transition-all"
        >
          ＋
        </button>
        <button
          onClick={() => handleZoom(0.8)}
          className="w-10 h-10 flex items-center justify-center bg-slate-800/85 hover:bg-slate-700 text-white rounded-lg border border-slate-700 font-bold transition-all"
        >
          －
        </button>
        <button
          onClick={() => {
            setZoom(0.8);
            setOffsetX(0);
            setOffsetY(0);
          }}
          className="px-3 h-10 flex items-center justify-center bg-slate-800/85 hover:bg-slate-700 text-white rounded-lg border border-slate-700 font-medium text-xs transition-all"
        >
          Reset View
        </button>
      </div>

      <canvas
        ref={canvasRef}
        width={750}
        height={500}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUpOrLeave}
        onMouseLeave={handleMouseUpOrLeave}
        onClick={handleClick}
        className="w-full h-[500px] cursor-grab active:cursor-grabbing block"
      />
    </div>
  );
};
