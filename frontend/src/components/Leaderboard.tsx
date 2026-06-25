import React from "react";
import { Trophy, TrendingUp, Heart, Clock, Coins } from "lucide-react";

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

interface LeaderboardProps {
  agents: AgentData[];
  onSelectAgent: (agent: AgentData | null) => void;
}

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

export const Leaderboard: React.FC<LeaderboardProps> = ({ agents, onSelectAgent }) => {
  const aliveAgents = agents.filter((a) => a.is_alive);

  const byMoney = [...aliveAgents].sort((a, b) => b.money - a.money).slice(0, 10);
  const byHappiness = [...aliveAgents].sort((a, b) => b.happiness - a.happiness).slice(0, 10);
  const byAge = [...aliveAgents].sort((a, b) => b.age - a.age).slice(0, 10);
  const byChildren = [...aliveAgents].sort((a, b) => b.children_count - a.children_count).slice(0, 10);

  const maxMoney = byMoney[0]?.money || 1;
  const maxHappiness = byHappiness[0]?.happiness || 1;
  const maxAge = byAge[0]?.age || 1;
  const maxChildren = byChildren[0]?.children_count || 1;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-xl p-4 max-h-[420px] overflow-y-auto scrollbar-thin">
      <h3 className="font-semibold text-slate-200 mb-4 flex items-center gap-2">
        <Trophy size={16} className="text-amber-400" />
        Leaderboards
      </h3>

      <div className="space-y-5">
        <LeaderboardSection
          title="Wealthiest Citizens"
          icon={<Coins size={12} className="text-emerald-400" />}
          agents={byMoney}
          valueKey="money"
          maxValue={maxMoney}
          format={(v) => `$${Math.round(v)}`}
          color="bg-emerald-500"
          onSelectAgent={onSelectAgent}
        />
        <LeaderboardSection
          title="Happiest Citizens"
          icon={<Heart size={12} className="text-rose-400" />}
          agents={byHappiness}
          valueKey="happiness"
          maxValue={maxHappiness}
          format={(v) => `${Math.round(v)}%`}
          color="bg-rose-500"
          onSelectAgent={onSelectAgent}
        />
        <LeaderboardSection
          title="Oldest Citizens"
          icon={<Clock size={12} className="text-sky-400" />}
          agents={byAge}
          valueKey="age"
          maxValue={maxAge}
          format={(v) => `${v} yrs`}
          color="bg-sky-500"
          onSelectAgent={onSelectAgent}
        />
        <LeaderboardSection
          title="Most Prolific Parents"
          icon={<TrendingUp size={12} className="text-indigo-400" />}
          agents={byChildren}
          valueKey="children_count"
          maxValue={maxChildren}
          format={(v) => `${v} kids`}
          color="bg-indigo-500"
          onSelectAgent={onSelectAgent}
        />
      </div>
    </div>
  );
};

interface LeaderboardSectionProps {
  title: string;
  icon: React.ReactNode;
  agents: AgentData[];
  valueKey: "money" | "happiness" | "age" | "children_count";
  maxValue: number;
  format: (value: number) => string;
  color: string;
  onSelectAgent: (agent: AgentData) => void;
}

const LeaderboardSection: React.FC<LeaderboardSectionProps> = ({
  title,
  icon,
  agents,
  valueKey,
  maxValue,
  format,
  color,
  onSelectAgent,
}) => {
  if (agents.length === 0) return null;

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{title}</span>
      </div>
      <div className="space-y-1.5">
        {agents.map((agent, idx) => {
          const value = agent[valueKey];
          const pct = maxValue > 0 ? (value / maxValue) * 100 : 0;
          const roleColor = ROLE_COLORS[agent.role] || "#e5e7eb";

          return (
            <button
              key={agent.id}
              onClick={() => onSelectAgent(agent)}
              className="w-full text-left group"
            >
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-500 font-mono w-4 text-right">{idx + 1}</span>
                <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: roleColor }} />
                <span className="text-slate-300 flex-1 truncate group-hover:text-white transition-colors">
                  {agent.name}
                </span>
                <span className="text-slate-400 font-mono">{format(value)}</span>
              </div>
              <div className="ml-7 mt-0.5 w-full bg-slate-950 rounded-full h-1 overflow-hidden">
                <div
                  className={`h-full rounded-full ${color} opacity-70`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
