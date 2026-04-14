"use client";

const COLORS: Record<string, string> = {
  World: "bg-blue-500",
  Sports: "bg-green-500",
  Business: "bg-yellow-500",
  Technology: "bg-purple-500",
};

interface Props {
  probabilities: Record<string, number>;
}

export default function ConfidenceBar({ probabilities }: Props) {
  return (
    <div className="space-y-2">
      {Object.entries(probabilities).map(([label, prob]) => (
        <div key={label} className="flex items-center gap-2">
          <span className="w-24 text-sm text-gray-600">{label}</span>
          <div className="flex-1 bg-gray-200 rounded-full h-4">
            <div
              className={`h-4 rounded-full ${COLORS[label] || "bg-gray-500"}`}
              style={{ width: `${(prob * 100).toFixed(1)}%` }}
            />
          </div>
          <span className="w-14 text-sm text-right">{(prob * 100).toFixed(1)}%</span>
        </div>
      ))}
    </div>
  );
}
