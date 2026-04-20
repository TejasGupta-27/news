"use client";
import useSWR from "swr";
import { fetcher, api } from "@/lib/api";
import { DriftLatestByModelResponse, DriftReport } from "@/lib/types";
import DriftChart from "@/components/DriftChart";
import { useState } from "react";
import { AlertTriangle, BarChart3, CheckCircle2 } from "lucide-react";
import {
  getLatestReportsByModel,
  getModelLabel,
  groupReportsByModel,
  hasDrift,
  normalizeModelVersion,
  sortModelVersions,
} from "@/lib/drift";

export default function MonitorPage() {
  const { data, mutate } = useSWR<{ items: DriftReport[] }>("/drift/history?days=30", fetcher, {
    refreshInterval: 60000,
  });
  const { data: latestByModel } = useSWR<DriftLatestByModelResponse>(
    "/drift/latest-by-model",
    fetcher,
    { refreshInterval: 60000 }
  );
  const [checking, setChecking] = useState(false);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);

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
  const latestReports = latestByModel
    ? Object.values(latestByModel).filter((report): report is DriftReport => !!report)
    : Object.values(getLatestReportsByModel(reports));
  const groupedReports = groupReportsByModel(reports);
  const modelVersions = sortModelVersions(Object.keys(groupedReports));
  const selectedVersions = selectedModel ? [selectedModel] : modelVersions;
  const chartGroups = selectedVersions
    .map((version) => ({
      version,
      label: getModelLabel(version),
      latest:
        latestReports.find(
          (report) => normalizeModelVersion(report.model_version) === version
        ) || null,
      reports: groupedReports[version] || [],
    }))
    .filter((group) => group.reports.length > 0);
  const filteredReports = selectedModel
    ? reports.filter((r) => normalizeModelVersion(r.model_version) === selectedModel)
    : reports;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent mb-2">
            Drift Monitor
          </h1>
          <p className="text-gray-400">Track data and prediction quality over time</p>
        </div>
        <button
          onClick={runCheck}
          disabled={checking}
          className="bg-gradient-to-r from-cyan-500 to-blue-500 text-white px-6 py-3 rounded-xl hover:shadow-lg hover:shadow-cyan-500/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium"
        >
          {checking ? "Checking..." : "Run Check Now"}
        </button>
      </div>

      {/* Model Filter */}
      {modelVersions.length > 0 && (
        <div className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl shadow-2xl p-6 backdrop-blur-sm border border-slate-600">
          <p className="text-sm font-medium text-gray-300 uppercase tracking-wide mb-4">
            Filter by Model Version
          </p>
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => setSelectedModel(null)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                selectedModel === null
                  ? "bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-lg shadow-cyan-500/50"
                  : "bg-slate-900/50 text-gray-300 hover:bg-slate-800/50 border border-slate-700"
              }`}
            >
              All Models
            </button>
            {modelVersions.map((version) => (
              <button
                key={version}
                onClick={() => setSelectedModel(version)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  selectedModel === version
                    ? "bg-gradient-to-r from-cyan-500 to-blue-500 text-white shadow-lg shadow-cyan-500/50"
                    : "bg-slate-900/50 text-gray-300 hover:bg-slate-800/50 border border-slate-700"
                }`}
              >
                {getModelLabel(version)}
              </button>
            ))}
          </div>
        </div>
      )}

      {chartGroups.length > 0 && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {chartGroups.map((group) => {
            const driftDetected = hasDrift(group.latest);

            return (
              <div
                key={group.version}
                className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl shadow-2xl p-6 backdrop-blur-sm border border-slate-600"
              >
                <div className="flex items-start justify-between gap-4 mb-6">
                  <div>
                    <p className="text-lg font-semibold text-cyan-400">{group.label}</p>
                    <p className="text-xs text-gray-500 mt-1 break-all">{group.version}</p>
                  </div>
                  <span
                    className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium ${
                      driftDetected
                        ? "bg-red-900/30 text-red-300 border border-red-500/50"
                        : "bg-green-900/30 text-green-300 border border-green-500/50"
                    }`}
                  >
                    {driftDetected ? (
                      <AlertTriangle className="w-4 h-4" />
                    ) : (
                      <CheckCircle2 className="w-4 h-4" />
                    )}
                    {group.latest
                      ? driftDetected
                        ? "Drift detected"
                        : "Stable"
                      : "No latest report"}
                  </span>
                </div>

                {group.latest && (
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
                    <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700">
                      <p className="text-xs text-gray-400 uppercase tracking-wide">Samples</p>
                      <p className="text-2xl font-bold text-cyan-400 mt-2">
                        {group.latest.sample_count}
                      </p>
                    </div>
                    <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700">
                      <p className="text-xs text-gray-400 uppercase tracking-wide">Label Drift</p>
                      <p className="text-lg font-bold text-blue-400 mt-2">
                        {group.latest.label_drift_detected ? "Detected" : "Normal"}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        p=
                        {group.latest.label_drift_pvalue !== null
                          ? group.latest.label_drift_pvalue < 0.001
                            ? group.latest.label_drift_pvalue.toExponential(2)
                            : group.latest.label_drift_pvalue.toFixed(4)
                          : "N/A"}
                      </p>
                    </div>
                    <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700">
                      <p className="text-xs text-gray-400 uppercase tracking-wide">
                        Confidence Drift
                      </p>
                      <p className="text-lg font-bold text-purple-400 mt-2">
                        {group.latest.confidence_drift_detected ? "Detected" : "Normal"}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        score=
                        {group.latest.confidence_drift_score !== null
                          ? group.latest.confidence_drift_score.toFixed(3)
                          : "N/A"}
                      </p>
                    </div>
                    <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700">
                      <p className="text-xs text-gray-400 uppercase tracking-wide">Last Check</p>
                      <p className="text-sm font-medium text-gray-200 mt-2">
                        {new Date(group.latest.check_time).toLocaleString()}
                      </p>
                      <p className="text-xs mt-1">
                        {group.latest.triggered_retraining ? (
                          <span className="text-amber-400">Retrain triggered</span>
                        ) : (
                          <span className="text-gray-500">No retrain triggered</span>
                        )}
                      </p>
                    </div>
                  </div>
                )}

                <DriftChart reports={group.reports} title={`${group.label} Trends`} />
              </div>
            );
          })}
        </div>
      )}

      {filteredReports.length > 0 ? (
        <>
          {/* Table */}
          <div className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-sm border border-slate-600">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-900/50 border-b border-slate-700">
                  <tr>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wide">
                      Time
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wide">
                      Model
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wide">
                      Samples
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wide">
                      Label Drift
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wide">
                      Confidence Drift
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-semibold text-gray-400 uppercase tracking-wide">
                      Retrain
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700">
                  {filteredReports.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-900/30 transition-colors">
                      <td className="px-6 py-4 text-sm text-gray-300">
                        {new Date(r.check_time).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 text-sm font-medium text-cyan-400">
                        {getModelLabel(r.model_version)}
                        <div className="text-xs text-gray-500 font-normal mt-1 break-all">
                          {normalizeModelVersion(r.model_version)}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-300">{r.sample_count}</td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-block px-3 py-1.5 rounded-lg text-xs font-medium ${
                            r.label_drift_detected
                              ? "bg-red-900/30 text-red-300 border border-red-500/50"
                              : "bg-green-900/30 text-green-300 border border-green-500/50"
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
                      <td className="px-6 py-4">
                        <span
                          className={`inline-block px-3 py-1.5 rounded-lg text-xs font-medium ${
                            r.confidence_drift_detected
                              ? "bg-red-900/30 text-red-300 border border-red-500/50"
                              : "bg-green-900/30 text-green-300 border border-green-500/50"
                          }`}
                        >
                          {r.confidence_drift_detected ? "Detected" : "Normal"}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm">
                        {r.triggered_retraining ? (
                          <span className="text-amber-400 font-medium">Yes</span>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        <div className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl shadow-2xl p-16 text-center backdrop-blur-sm border border-slate-600">
          <div className="flex justify-center mb-4">
            <BarChart3 className="w-16 h-16 text-slate-600" />
          </div>
          <p className="text-gray-400 text-lg">No drift reports yet.</p>
          <p className="text-gray-500 text-sm mt-2">Run a drift check or wait for the scheduler to complete a check.</p>
        </div>
      )}
    </div>
  );
}
