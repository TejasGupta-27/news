"use client";
import useSWR from "swr";
import { fetcher, api } from "@/lib/api";
import { DriftReport } from "@/lib/types";
import DriftChart from "@/components/DriftChart";
import { useState } from "react";

export default function MonitorPage() {
  const { data, mutate } = useSWR<{ items: DriftReport[] }>("/drift/history?days=30", fetcher, {
    refreshInterval: 60000,
  });
  const [checking, setChecking] = useState(false);

  const runCheck = async () => {
    setChecking(true);
    try {
      await api("/drift/check", { method: "POST" });
      mutate();
    } finally {
      setChecking(false);
    }
  };

  const reports = data?.items || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Drift Monitor</h1>
        <button
          onClick={runCheck}
          disabled={checking}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm"
        >
          {checking ? "Checking..." : "Run Check Now"}
        </button>
      </div>

      {reports.length > 0 ? (
        <>
          <div className="bg-white rounded-lg shadow p-6">
            <DriftChart reports={reports} />
          </div>

          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left">Time</th>
                  <th className="px-4 py-3 text-left">Samples</th>
                  <th className="px-4 py-3 text-left">Label Drift</th>
                  <th className="px-4 py-3 text-left">Confidence Drift</th>
                  <th className="px-4 py-3 text-left">Retrain</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr key={r.id} className="border-t">
                    <td className="px-4 py-3">{new Date(r.check_time).toLocaleString()}</td>
                    <td className="px-4 py-3">{r.sample_count}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs ${
                          r.label_drift_detected
                            ? "bg-red-100 text-red-800"
                            : "bg-green-100 text-green-800"
                        }`}
                      >
                        {r.label_drift_detected ? "Detected" : "Normal"}{" "}
                        {r.label_drift_pvalue !== null &&
                          `(p=${
                            r.label_drift_pvalue < 0.001
                              ? r.label_drift_pvalue.toExponential(2)
                              : r.label_drift_pvalue.toFixed(4)
                          })`}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs ${
                          r.confidence_drift_detected
                            ? "bg-red-100 text-red-800"
                            : "bg-green-100 text-green-800"
                        }`}
                      >
                        {r.confidence_drift_detected ? "Detected" : "Normal"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {r.triggered_retraining ? "Yes" : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center text-gray-500">
          No drift reports yet. Run a drift check or wait for the scheduler.
        </div>
      )}
    </div>
  );
}
