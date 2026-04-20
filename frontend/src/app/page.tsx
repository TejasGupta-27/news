"use client";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { DriftLatestByModelResponse, DriftReport, ModelInfo } from "@/lib/types";
import { Cpu, BarChart3, AlertTriangle, CheckCircle } from "lucide-react";
import {
  getModelLabel,
  hasDrift,
  normalizeModelVersion,
  sortModelVersions,
} from "@/lib/drift";

export default function Dashboard() {
  const { data: model } = useSWR<ModelInfo>("/model/info", fetcher, { refreshInterval: 30000 });
  const { data: latestByModel } = useSWR<DriftLatestByModelResponse>("/drift/latest-by-model", fetcher, {
    refreshInterval: 60000,
  });
  const { data: predictions } = useSWR<{ total: number }>("/predictions?limit=1", fetcher, {
    refreshInterval: 10000,
  });

  const driftReports = sortModelVersions(Object.keys(latestByModel || {}))
    .map((version) => latestByModel?.[version])
    .filter((report): report is DriftReport => !!report);
  const driftDetectedCount = driftReports.filter((report) => hasDrift(report)).length;
  const driftStatus = driftReports.length === 0 ? "No data" : driftDetectedCount > 0 ? "Detected" : "Normal";
  const driftColor =
    driftDetectedCount > 0
      ? "bg-gradient-to-r from-red-900/30 to-red-800/30 border-red-500/50 text-red-300"
      : "bg-gradient-to-r from-green-900/30 to-emerald-800/30 border-green-500/50 text-green-300";

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent mb-2">
          Dashboard
        </h1>
        <p className="text-gray-400">Real-time monitoring of your AI classification system</p>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Model Card */}
        <div className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl shadow-2xl p-8 backdrop-blur-sm border border-slate-600 hover:border-cyan-500/50 transition-colors">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-gray-400 uppercase tracking-wide">Model Version</p>
              <p className="text-2xl font-bold text-cyan-400 mt-2">
                {model?.version || "Loading..."}
              </p>
            </div>
            <Cpu className="w-8 h-8 text-cyan-400" />
          </div>
          <p className="text-xs text-gray-500">
            {model?.loaded ? (
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500"></span>
                Loaded
              </span>
            ) : (
              "Not loaded"
            )}
          </p>
        </div>

        {/* Predictions Card */}
        <div className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl shadow-2xl p-8 backdrop-blur-sm border border-slate-600 hover:border-blue-500/50 transition-colors">
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm text-gray-400 uppercase tracking-wide">Total Predictions</p>
              <p className="text-2xl font-bold text-blue-400 mt-2">
                {predictions?.total ?? "..."}
              </p>
            </div>
            <BarChart3 className="w-8 h-8 text-blue-400" />
          </div>
          <p className="text-xs text-gray-500">All-time predictions logged</p>
        </div>

        {/* Drift Status Card */}
        <div className={`bg-gradient-to-br rounded-2xl shadow-2xl p-8 backdrop-blur-sm border transition-colors ${driftColor}`}>
          <div className="flex items-start justify-between mb-4">
            <div>
              <p className="text-sm uppercase tracking-wide opacity-80">Drift Status</p>
              <p className="text-2xl font-bold mt-2">{driftStatus}</p>
            </div>
            {driftStatus === "Detected" ? (
              <AlertTriangle className="w-8 h-8 text-red-300" />
            ) : (
              <CheckCircle className="w-8 h-8 text-green-300" />
            )}
          </div>
          {driftReports.length > 0 ? (
            <div className="space-y-2">
              {driftReports.map((report) => (
                <div key={report.id} className="flex items-center justify-between gap-3 text-xs opacity-90">
                  <span>{getModelLabel(report.model_version)}</span>
                  <span>{hasDrift(report) ? "Detected" : "Normal"}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs opacity-80">No drift reports available yet.</p>
          )}
        </div>
      </div>

      {/* Drift Report Card */}
      {driftReports.length > 0 && (
        <div className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl shadow-2xl p-8 backdrop-blur-sm border border-slate-600">
          <h2 className="text-xl font-bold text-cyan-400 mb-6">Latest Drift by Model</h2>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {driftReports.map((report) => (
              <div key={report.id} className="bg-slate-900/50 rounded-2xl p-6 border border-slate-700">
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div>
                    <p className="text-lg font-semibold text-cyan-400">
                      {getModelLabel(report.model_version)}
                    </p>
                    <p className="text-xs text-gray-500 mt-1 break-all">
                      {normalizeModelVersion(report.model_version)}
                    </p>
                  </div>
                  <span
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium ${
                      hasDrift(report)
                        ? "bg-red-900/30 text-red-300 border border-red-500/50"
                        : "bg-green-900/30 text-green-300 border border-green-500/50"
                    }`}
                  >
                    {hasDrift(report) ? "Drift detected" : "Stable"}
                  </span>
                </div>

                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-slate-800/80 rounded-xl p-4 border border-slate-700">
                    <p className="text-xs text-gray-400 uppercase tracking-wide">Samples</p>
                    <p className="text-2xl font-bold text-cyan-400 mt-2">{report.sample_count}</p>
                  </div>
                  <div className="bg-slate-800/80 rounded-xl p-4 border border-slate-700">
                    <p className="text-xs text-gray-400 uppercase tracking-wide">Label Drift</p>
                    <p className="text-lg font-bold text-blue-400 mt-2">
                      {report.label_drift_detected ? "Detected" : "Normal"}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      p=
                      {report.label_drift_pvalue !== null
                        ? report.label_drift_pvalue < 0.001
                          ? report.label_drift_pvalue.toExponential(2)
                          : report.label_drift_pvalue.toFixed(4)
                        : "N/A"}
                    </p>
                  </div>
                  <div className="bg-slate-800/80 rounded-xl p-4 border border-slate-700">
                    <p className="text-xs text-gray-400 uppercase tracking-wide">Confidence</p>
                    <p className="text-lg font-bold text-purple-400 mt-2">
                      {report.confidence_drift_detected ? "Detected" : "Normal"}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      score=
                      {report.confidence_drift_score !== null
                        ? report.confidence_drift_score.toFixed(3)
                        : "N/A"}
                    </p>
                  </div>
                  <div className="bg-slate-800/80 rounded-xl p-4 border border-slate-700">
                    <p className="text-xs text-gray-400 uppercase tracking-wide">Retraining</p>
                    <p className="text-lg font-bold mt-2">
                      {report.triggered_retraining ? (
                        <span className="text-amber-400">Triggered</span>
                      ) : (
                        <span className="text-green-400">Idle</span>
                      )}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
