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
}

export default function DriftChart({ reports }: Props) {
  const data = [...reports].reverse().map((r) => ({
    time: new Date(r.check_time).toLocaleString(),
    pvalue: r.label_drift_pvalue,
    confScore: r.confidence_drift_score,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-2">Label Drift (p-value)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <XAxis dataKey="time" tick={{ fontSize: 10 }} />
            <YAxis domain={[0, 1]} />
            <Tooltip />
            <ReferenceLine y={0.05} stroke="red" strokeDasharray="3 3" label="Threshold" />
            <Line type="monotone" dataKey="pvalue" stroke="#3b82f6" dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-2">Confidence Drift Score</h3>
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
