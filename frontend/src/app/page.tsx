"use client";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { ModelInfo, DriftReport } from "@/lib/types";

export default function Dashboard() {
  const { data: model } = useSWR<ModelInfo>("/model/info", fetcher, { refreshInterval: 30000 });
  const { data: drift } = useSWR<DriftReport | null>("/drift/latest", fetcher, {
    refreshInterval: 60000,
  });
  const { data: predictions } = useSWR<{ total: number }>("/predictions?limit=1", fetcher, {
    refreshInterval: 10000,
  });

  const driftStatus =
    drift?.label_drift_detected || drift?.confidence_drift_detected ? "Detected" : "Normal";
  const driftColor =
    drift?.label_drift_detected || drift?.confidence_drift_detected
      ? "bg-red-100 text-red-800"
      : "bg-green-100 text-green-800";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Model Version</p>
          <p className="text-xl font-semibold">{model?.version || "Loading..."}</p>
          <p className="text-xs text-gray-400 mt-1">
            {model?.loaded ? "Loaded" : "Not loaded"}
          </p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Total Predictions</p>
          <p className="text-xl font-semibold">{predictions?.total ?? "..."}</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-sm text-gray-500">Drift Status</p>
          <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${driftColor}`}>
            {drift ? driftStatus : "No data"}
          </span>
          {drift && (
            <p className="text-xs text-gray-400 mt-2">
              Last check: {new Date(drift.check_time).toLocaleString()}
            </p>
          )}
        </div>
      </div>

      {drift && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-3">Latest Drift Report</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Samples</p>
              <p className="font-medium">{drift.sample_count}</p>
            </div>
            <div>
              <p className="text-gray-500">Label Drift p-value</p>
              <p className="font-medium">{drift.label_drift_pvalue?.toFixed(4) ?? "N/A"}</p>
            </div>
            <div>
              <p className="text-gray-500">Confidence Drift</p>
              <p className="font-medium">
                {drift.confidence_drift_detected ? "Yes" : "No"}
              </p>
            </div>
            <div>
              <p className="text-gray-500">Triggered Retraining</p>
              <p className="font-medium">{drift.triggered_retraining ? "Yes" : "No"}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
