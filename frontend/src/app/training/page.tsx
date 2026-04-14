"use client";
import useSWR from "swr";
import { fetcher, api } from "@/lib/api";
import { TrainingRun } from "@/lib/types";
import { useState } from "react";

const STATUS_COLORS: Record<string, string> = {
  running: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  rejected: "bg-yellow-100 text-yellow-800",
};

export default function TrainingPage() {
  const { data, mutate } = useSWR<{ items: TrainingRun[] }>("/training/runs", fetcher, {
    refreshInterval: 10000,
  });
  const [triggering, setTriggering] = useState(false);

  const triggerRetrain = async () => {
    setTriggering(true);
    try {
      await api("/training/trigger", { method: "POST" });
      mutate();
    } finally {
      setTriggering(false);
    }
  };

  const runs = data?.items || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Training History</h1>
        <button
          onClick={triggerRetrain}
          disabled={triggering}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          {triggering ? "Triggering..." : "Trigger Retraining"}
        </button>
      </div>

      {runs.length > 0 ? (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left">Started</th>
                <th className="px-4 py-3 text-left">Reason</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Accuracy</th>
                <th className="px-4 py-3 text-left">F1 Macro</th>
                <th className="px-4 py-3 text-left">Prev F1</th>
                <th className="px-4 py-3 text-left">Deployed</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id} className="border-t">
                  <td className="px-4 py-3">{new Date(r.started_at).toLocaleString()}</td>
                  <td className="px-4 py-3">{r.trigger_reason}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-xs ${
                        STATUS_COLORS[r.status] || "bg-gray-100"
                      }`}
                    >
                      {r.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {r.accuracy !== null ? (r.accuracy * 100).toFixed(2) + "%" : "-"}
                  </td>
                  <td className="px-4 py-3">
                    {r.f1_macro !== null ? (r.f1_macro * 100).toFixed(2) + "%" : "-"}
                  </td>
                  <td className="px-4 py-3">
                    {r.previous_f1 !== null ? (r.previous_f1 * 100).toFixed(2) + "%" : "-"}
                  </td>
                  <td className="px-4 py-3">{r.deployed ? "Yes" : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center text-gray-500">
          No training runs yet.
        </div>
      )}
    </div>
  );
}
