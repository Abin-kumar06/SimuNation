import React, { useState } from "react";

interface Policy {
  tax_rate: number;
  welfare_amount: number;
  welfare_money_threshold: number;
  welfare_food_threshold: number;
}

interface ControlPanelProps {
  policy: Policy;
  onStep: (count: number) => void;
  onReset: () => void;
  onApplyPolicy: (policy: Policy) => void;
  onTriggerEvent: (eventName: string) => void;
  isAutoplay: boolean;
  onToggleAutoplay: () => void;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({
  policy,
  onStep,
  onReset,
  onApplyPolicy,
  onTriggerEvent,
  isAutoplay,
  onToggleAutoplay
}) => {
  const [tax, setTax] = useState<number>(Math.round(policy.tax_rate * 100));
  const [wAmount, setWAmount] = useState<number>(policy.welfare_amount);
  const [wMoney, setWMoney] = useState<number>(policy.welfare_money_threshold);
  const [wFood, setWFood] = useState<number>(policy.welfare_food_threshold);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onApplyPolicy({
      tax_rate: tax / 100,
      welfare_amount: wAmount,
      welfare_money_threshold: wMoney,
      welfare_food_threshold: wFood
    });
  };

  const events = ["Drought", "Disease Outbreak", "Economic Boom", "Resource Discovery", "Market Crash"];

  return (
    <div className="flex flex-col gap-6">
      {/* Simulation Steppers */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
        <h3 className="font-semibold text-slate-200 mb-4 flex items-center gap-2">
          ⚙️ Simulation Controls
        </h3>
        <div className="grid grid-cols-2 gap-3 mb-4">
          <button
            onClick={() => onStep(1)}
            className="py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 font-semibold text-sm rounded-lg text-white transition-all shadow-lg"
          >
            Step 1
          </button>
          <button
            onClick={() => onStep(10)}
            className="py-2.5 px-4 bg-slate-800 hover:bg-slate-750 font-semibold text-sm rounded-lg text-slate-200 border border-slate-700 transition-all"
          >
            Step 10
          </button>
          <button
            onClick={onToggleAutoplay}
            className={`col-span-2 py-2.5 px-4 font-semibold text-sm rounded-lg transition-all shadow-md ${
              isAutoplay
                ? "bg-amber-600 hover:bg-amber-500 text-white"
                : "bg-emerald-600 hover:bg-emerald-500 text-white"
            }`}
          >
            {isAutoplay ? "⏸️ Pause Auto-step" : "▶️ Auto-step (Play)"}
          </button>
          <button
            onClick={onReset}
            className="col-span-2 py-2 px-4 bg-rose-950/40 hover:bg-rose-900/40 border border-rose-800/40 text-rose-400 font-semibold text-xs rounded-lg transition-all"
          >
            Reset Simulation
          </button>
        </div>
      </div>

      {/* Govt Policies Slider */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
        <h3 className="font-semibold text-slate-200 mb-4 flex items-center gap-2">
          🏛️ Government Policy
        </h3>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <div className="flex justify-between text-xs text-slate-400 mb-1">
              <span>Tax Rate</span>
              <span className="text-indigo-400 font-bold">{tax}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="30"
              value={tax}
              onChange={(e) => setTax(Number(e.target.value))}
              className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-indigo-600"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs text-slate-400 mb-1">
              <span>Welfare Payout</span>
              <span className="text-indigo-400 font-bold">${wAmount}</span>
            </div>
            <input
              type="range"
              min="0"
              max="50"
              value={wAmount}
              onChange={(e) => setWAmount(Number(e.target.value))}
              className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-indigo-600"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs text-slate-400 mb-1">
              <span>Welfare Money Trigger</span>
              <span className="text-indigo-400 font-bold">${wMoney}</span>
            </div>
            <input
              type="range"
              min="0"
              max="50"
              value={wMoney}
              onChange={(e) => setWMoney(Number(e.target.value))}
              className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-indigo-600"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs text-slate-400 mb-1">
              <span>Welfare Food Trigger</span>
              <span className="text-indigo-400 font-bold">{wFood}</span>
            </div>
            <input
              type="range"
              min="0"
              max="10"
              step="0.5"
              value={wFood}
              onChange={(e) => setWFood(Number(e.target.value))}
              className="w-full h-1 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-indigo-600"
            />
          </div>

          <button
            type="submit"
            className="w-full py-2 bg-indigo-600/10 hover:bg-indigo-600 text-indigo-400 hover:text-white border border-indigo-500/30 text-xs font-semibold rounded-lg transition-all"
          >
            Apply Fiscal Policies
          </button>
        </form>
      </div>

      {/* Manual Events */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl">
        <h3 className="font-semibold text-slate-200 mb-4 flex items-center gap-2">
          🌪️ Inject World Event
        </h3>
        <div className="flex flex-col gap-2">
          {events.map((evt) => (
            <button
              key={evt}
              onClick={() => onTriggerEvent(evt)}
              className="w-full py-2 bg-slate-950 hover:bg-slate-850 hover:text-indigo-400 border border-slate-800 text-slate-300 font-medium text-xs rounded-lg transition-all text-left px-3 flex justify-between items-center"
            >
              <span>{evt}</span>
              <span className="text-slate-500 font-semibold">⚡ Inject</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
