"use client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { DriftReport } from "@/lib/types";

interface Props {
  reports: DriftReport[];
  title?: string;
}

export default function DriftChart({ reports, title }: Props) {
  const MIN_P = 1e-300;
  const data = [...reports].reverse().map((r) => ({
    time: new Date(r.check_time).toLocaleString(),
    pvalue: Math.max(r.label_drift_pvalue ?? 1, MIN_P),
    pvalueRaw: r.label_drift_pvalue,
    confScore: r.confidence_drift_score,
  }));

  const fmt = (v: number) => {
    if (v === 0 || v === null || v === undefined) return "0";
    if (v < 0.001 || v > 1000) return v.toExponential(2);
    return v.toFixed(3);
  };

  return (
    <div className="space-y-6">
      {title && <h3 className="text-lg font-semibold text-cyan-400">{title}</h3>}
      <div>
        <h4 className="text-sm font-medium text-gray-300 mb-2">
          Label Drift (p-value, log scale)
        </h4>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <XAxis dataKey="time" tick={{ fontSize: 10 }} />
            <YAxis
              scale="log"
              domain={[MIN_P, 1]}
              tickFormatter={fmt}
              tick={{ fontSize: 10 }}
              allowDataOverflow
            />
            <Tooltip formatter={(v: number) => fmt(v)} />
            <ReferenceLine
              y={0.05}
              stroke="red"
              strokeDasharray="3 3"
              label={{ value: "Threshold (0.05)", position: "insideTopRight", fontSize: 10 }}
            />
            <Line type="monotone" dataKey="pvalue" stroke="#3b82f6" dot={{ r: 3 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div>
        <h4 className="text-sm font-medium text-gray-300 mb-2">Confidence Drift Score</h4>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <XAxis dataKey="time" tick={{ fontSize: 10 }} />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="confScore" stroke="#8b5cf6" dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
