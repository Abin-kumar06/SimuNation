import React, { useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  Cell
} from "recharts";

interface StatsDashboardProps {
  history: any[];
}

const COLORS = ["#10b981", "#fb923c", "#3b82f6", "#a855f7", "#ec4899", "#f59e0b", "#06b6d4", "#e5e7eb"];

export const StatsDashboard: React.FC<StatsDashboardProps> = ({ history }) => {
  const [tab, setTab] = useState<"economy" | "population" | "inequality" | "professions">("economy");

  const latestStats = history[history.length - 1] || {};
  const roleAnalytics = latestStats.role_analytics || {};

  const barData = Object.entries(roleAnalytics).map(([role, stats]: [string, any]) => ({
    name: role,
    count: stats.count,
    avgMoney: stats.avg_money,
    avgFood: stats.avg_food
  }));

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
      <div className="flex justify-between items-center border-b border-slate-800 pb-4 mb-4">
        <h3 className="font-semibold text-lg text-slate-100 flex items-center gap-2">
          📊 Analytics Dashboard
        </h3>
        <div className="flex gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
          {(["economy", "population", "inequality", "professions"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md uppercase tracking-wider transition-all ${
                tab === t
                  ? "bg-indigo-600 text-white shadow-md"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className="h-[280px] w-full">
        {history.length < 2 && tab !== "professions" ? (
          <div className="w-full h-full flex flex-col items-center justify-center text-slate-500 text-sm">
            <span>Graph data will accumulate once the simulation runs.</span>
          </div>
        ) : (
          <>
            {tab === "economy" && (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="timestep" stroke="#6b7280" fontSize={11} />
                  <YAxis yAxisId="left" stroke="#10b981" fontSize={11} />
                  <YAxis yAxisId="right" orientation="right" stroke="#38bdf8" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: "#0b0f19", borderColor: "#334155", color: "#f3f4f6" }} />
                  <Legend />
                  <Line yAxisId="left" type="monotone" dataKey="average_food_price" stroke="#10b981" name="Food Price ($)" strokeWidth={2} dot={false} />
                  <Line yAxisId="right" type="monotone" dataKey="total_food" stroke="#38bdf8" name="Total Food Supply" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}

            {tab === "population" && (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="timestep" stroke="#6b7280" fontSize={11} />
                  <YAxis stroke="#f43f5e" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: "#0b0f19", borderColor: "#334155", color: "#f3f4f6" }} />
                  <Legend />
                  <Line type="monotone" dataKey="population_alive" stroke="#10b981" name="Alive" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="population_starving" stroke="#f97316" name="Starving" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="population_dead" stroke="#f43f5e" name="Deceased" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}

            {tab === "inequality" && (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="timestep" stroke="#6b7280" fontSize={11} />
                  <YAxis domain={[0, 1]} stroke="#6366f1" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: "#0b0f19", borderColor: "#334155", color: "#f3f4f6" }} />
                  <Legend />
                  <Line type="monotone" dataKey="gini_coefficient" stroke="#6366f1" name="Gini Inequality Coeff" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            )}

            {tab === "professions" && barData.length === 0 ? (
              <div className="w-full h-full flex items-center justify-center text-slate-500 text-sm">
                No active demographics yet.
              </div>
            ) : tab === "professions" ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={barData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="name" stroke="#6b7280" fontSize={11} />
                  <YAxis stroke="#e2e8f0" fontSize={11} />
                  <Tooltip contentStyle={{ backgroundColor: "#0b0f19", borderColor: "#334155", color: "#f3f4f6" }} />
                  <Legend />
                  <Bar dataKey="count" fill="#4f46e5" name="Population Count">
                    {barData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                  <Bar dataKey="avgMoney" fill="#10b981" name="Avg Wealth ($)" />
                </BarChart>
              </ResponsiveContainer>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
};
