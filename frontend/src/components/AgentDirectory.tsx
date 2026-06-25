import React, { useState, useMemo } from "react";
import { Search, Filter, ChevronDown, ChevronUp, User, Skull, AlertTriangle, Coins, Heart } from "lucide-react";

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

interface AgentDirectoryProps {
  agents: AgentData[];
  selectedAgentId: number | null;
  onSelectAgent: (agent: AgentData | null) => void;
}

const ROLE_OPTIONS = ["Farmer", "Miner", "Builder", "Doctor", "Teacher", "Worker", "Trader", "Merchant", "Child"];

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

export const AgentDirectory: React.FC<AgentDirectoryProps> = ({
  agents,
  selectedAgentId,
  onSelectAgent,
}) => {
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "alive" | "starving" | "dead">("all");
  const [sortBy, setSortBy] = useState<"name" | "money" | "happiness" | "health" | "age" | "food" | "children">("money");
  const [sortDir, setSortDir] = useState<"desc" | "asc">("desc");
  const [collapsed, setCollapsed] = useState(false);

  const filteredAgents = useMemo(() => {
    let result = [...agents];

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (a) =>
          a.name.toLowerCase().includes(q) ||
          String(a.id).includes(q) ||
          a.role.toLowerCase().includes(q)
      );
    }

    if (roleFilter !== "all") {
      result = result.filter((a) => a.role === roleFilter);
    }

    if (statusFilter !== "all") {
      if (statusFilter === "dead") result = result.filter((a) => !a.is_alive);
      else if (statusFilter === "starving") result = result.filter((a) => a.is_alive && a.starving);
      else if (statusFilter === "alive") result = result.filter((a) => a.is_alive);
    }

    result.sort((a, b) => {
      const getVal = (agent: AgentData, key: typeof sortBy): number | string => {
        if (key === "children") return agent.children_count;
        const v = (agent as any)[key];
        return typeof v === "string" ? v.toLowerCase() : v;
      };
      const valA = getVal(a, sortBy);
      const valB = getVal(b, sortBy);
      if (valA < valB) return sortDir === "asc" ? -1 : 1;
      if (valA > valB) return sortDir === "asc" ? 1 : -1;
      return 0;
    });

    return result;
  }, [agents, search, roleFilter, statusFilter, sortBy, sortDir]);

  const toggleSort = (field: typeof sortBy) => {
    if (sortBy === field) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"));
    } else {
      setSortBy(field);
      setSortDir("desc");
    }
  };

  const SortIcon = ({ field }: { field: typeof sortBy }) => {
    if (sortBy !== field) return <span className="text-slate-600 ml-1">↕</span>;
    return sortDir === "desc" ? (
      <ChevronDown size={12} className="ml-1 text-indigo-400" />
    ) : (
      <ChevronUp size={12} className="ml-1 text-indigo-400" />
    );
  };

  const aliveCount = agents.filter((a) => a.is_alive).length;
  const starvingCount = agents.filter((a) => a.is_alive && a.starving).length;
  const deadCount = agents.filter((a) => !a.is_alive).length;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-xl flex flex-col max-h-[420px]">
      {/* Header */}
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-slate-200 flex items-center gap-2">
            <UsersIcon size={16} className="text-indigo-400" />
            Population Directory
          </h3>
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="text-slate-500 hover:text-slate-300 text-xs font-bold"
          >
            {collapsed ? "Expand" : "Collapse"}
          </button>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-3 gap-2 mb-3">
          <div className="bg-slate-950 rounded-lg p-2 text-center border border-slate-800">
            <div className="text-emerald-400 font-bold text-lg">{aliveCount}</div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Alive</div>
          </div>
          <div className="bg-slate-950 rounded-lg p-2 text-center border border-slate-800">
            <div className="text-orange-400 font-bold text-lg">{starvingCount}</div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Starving</div>
          </div>
          <div className="bg-slate-950 rounded-lg p-2 text-center border border-slate-800">
            <div className="text-rose-500 font-bold text-lg">{deadCount}</div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Dead</div>
          </div>
        </div>

        {!collapsed && (
          <>
            {/* Search */}
            <div className="relative mb-3">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                placeholder="Search by name, ID, or role..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/50 transition-colors"
              />
            </div>

            {/* Filters */}
            <div className="flex gap-2 flex-wrap">
              <select
                value={roleFilter}
                onChange={(e) => setRoleFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500/50"
              >
                <option value="all">All Roles</option>
                {ROLE_OPTIONS.map((r) => (
                  <option key={r} value={r}>
                    {r}
                  </option>
                ))}
              </select>

              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500/50"
              >
                <option value="all">All Status</option>
                <option value="alive">Alive</option>
                <option value="starving">Starving</option>
                <option value="dead">Dead</option>
              </select>

              <div className="text-[10px] text-slate-500 flex items-center ml-auto">
                <Filter size={10} className="mr-1" />
                {filteredAgents.length} result{filteredAgents.length !== 1 ? "s" : ""}
              </div>
            </div>
          </>
        )}
      </div>

      {/* Column Headers */}
      {!collapsed && (
        <div className="grid grid-cols-[1fr_60px_60px_60px_50px] gap-1 px-4 py-2 text-[10px] text-slate-500 uppercase tracking-wider border-b border-slate-800 bg-slate-950/50">
          <button onClick={() => toggleSort("name" as any)} className="text-left flex items-center">
            Name <SortIcon field="name" />
          </button>
          <button onClick={() => toggleSort("money")} className="text-right flex items-center justify-end">
            <Coins size={10} className="mr-1" /> <SortIcon field="money" />
          </button>
          <button onClick={() => toggleSort("happiness")} className="text-right flex items-center justify-end">
            <Heart size={10} className="mr-1" /> <SortIcon field="happiness" />
          </button>
          <button onClick={() => toggleSort("age")} className="text-right flex items-center justify-end">
            Age <SortIcon field="age" />
          </button>
          <button onClick={() => toggleSort("health")} className="text-right flex items-center justify-end">
            HP <SortIcon field="health" />
          </button>
        </div>
      )}

      {/* Agent List */}
      {!collapsed && (
        <div className="overflow-y-auto scrollbar-thin flex-1 p-2 space-y-1">
          {filteredAgents.length === 0 ? (
            <div className="text-center text-slate-500 text-xs py-8">No agents match your filters.</div>
          ) : (
            filteredAgents.map((agent) => {
              const isSelected = selectedAgentId === agent.id;
              const roleColor = ROLE_COLORS[agent.role] || "#e5e7eb";

              return (
                <button
                  key={agent.id}
                  onClick={() => onSelectAgent(isSelected ? null : agent)}
                  className={`w-full grid grid-cols-[1fr_60px_60px_60px_50px] gap-1 items-center px-3 py-2 rounded-lg text-xs transition-all text-left ${
                    isSelected
                      ? "bg-indigo-600/15 border border-indigo-500/30"
                      : "bg-slate-950/50 border border-slate-800/50 hover:bg-slate-800/50 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <div
                      className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ backgroundColor: roleColor }}
                    />
                    {!agent.is_alive ? (
                      <Skull size={12} className="text-rose-500 flex-shrink-0" />
                    ) : agent.starving ? (
                      <AlertTriangle size={12} className="text-orange-400 flex-shrink-0" />
                    ) : (
                      <User size={12} className="text-emerald-400 flex-shrink-0" />
                    )}
                    <div className="min-w-0">
                      <div className={`font-medium truncate ${!agent.is_alive ? "text-slate-500 line-through" : "text-slate-200"}`}>
                        {agent.name}
                      </div>
                      <div className="text-[10px] text-slate-500 truncate">
                        #{agent.id} · {agent.role}
                      </div>
                    </div>
                  </div>

                  <div className={`text-right font-semibold ${!agent.is_alive ? "text-slate-600" : "text-emerald-400"}`}>
                    ${Math.round(agent.money)}
                  </div>
                  <div className={`text-right font-semibold ${!agent.is_alive ? "text-slate-600" : agent.happiness > 60 ? "text-sky-400" : agent.happiness > 30 ? "text-amber-400" : "text-rose-400"}`}>
                    {Math.round(agent.happiness)}
                  </div>
                  <div className={`text-right ${!agent.is_alive ? "text-slate-600" : "text-slate-300"}`}>
                    {agent.age}
                  </div>
                  <div className="text-right">
                    <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          agent.health > 60 ? "bg-emerald-500" : agent.health > 30 ? "bg-amber-500" : "bg-rose-500"
                        }`}
                        style={{ width: `${agent.health}%` }}
                      />
                    </div>
                  </div>
                </button>
              );
            })
          )}
        </div>
      )}
    </div>
  );
};

function UsersIcon({ size, className }: { size: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}
