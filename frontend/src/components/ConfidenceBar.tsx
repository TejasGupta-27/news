"use client";

const COLORS: Record<string, string> = {
  World: "bg-gradient-to-r from-blue-500 to-cyan-400",
  Sports: "bg-gradient-to-r from-green-500 to-emerald-400",
  Business: "bg-gradient-to-r from-amber-500 to-orange-400",
  Technology: "bg-gradient-to-r from-purple-500 to-indigo-400",
};

interface Props {
  probabilities: Record<string, number>;
}

export default function ConfidenceBar({ probabilities }: Props) {
  const sorted = Object.entries(probabilities).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-4">
      <p className="text-sm font-medium text-gray-400 uppercase tracking-wide">
        Classification Probabilities
      </p>
      {sorted.map(([label, prob]) => (
        <div key={label} className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-300">{label}</span>
            <span className="text-sm font-bold text-cyan-400">{(prob * 100).toFixed(1)}%</span>
          </div>
          <div className="h-3 bg-slate-900 rounded-full overflow-hidden border border-slate-700">
            <div
              className={`h-3 rounded-full ${COLORS[label] || "bg-slate-500"} shadow-lg transition-all`}
              style={{ width: `${(prob * 100).toFixed(1)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
