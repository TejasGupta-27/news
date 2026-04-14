"use client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

interface Props {
  explanation: { token: string; score: number }[];
}

export default function ExplanationChart({ explanation }: Props) {
  const sorted = [...explanation]
    .sort((a, b) => Math.abs(b.score) - Math.abs(a.score))
    .slice(0, 20);

  return (
    <div className="mt-4">
      <h3 className="text-sm font-medium text-gray-700 mb-2">Token Attributions (Top 20)</h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={sorted} layout="vertical">
          <XAxis type="number" />
          <YAxis type="category" dataKey="token" width={80} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="score">
            {sorted.map((entry, i) => (
              <Cell key={i} fill={entry.score >= 0 ? "#22c55e" : "#ef4444"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
