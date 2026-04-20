"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { CheckCircle, AlertCircle, TrendingUp, BarChart3, Code, Info } from "lucide-react";
import type {
  AbSettingsResponse,
  AbStatsResponse,
  PairwiseCreateResponse,
  PairwiseOption,
} from "@/lib/types";

const LABEL_COLORS: Record<string, string> = {
  World: "bg-blue-500/20 text-blue-300 border border-blue-500/50",
  Sports: "bg-green-500/20 text-green-300 border border-green-500/50",
  Business: "bg-yellow-500/20 text-yellow-300 border border-yellow-500/50",
  Technology: "bg-purple-500/20 text-purple-300 border border-purple-500/50",
};

function OptionCard({
  title,
  option,
  onPick,
  disabled,
}: {
  title: string;
  option: PairwiseOption;
  onPick: () => void;
  disabled: boolean;
}) {
  return (
    <div className="border border-slate-600 rounded-xl p-6 space-y-3 flex flex-col bg-gradient-to-br from-slate-800 to-slate-700 hover:border-slate-500 transition-colors">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-gray-300">{title}</span>
        <span
          className={`px-3 py-1 rounded-full text-xs font-medium ${
            LABEL_COLORS[option.label] || "bg-gray-700/50 text-gray-300 border border-gray-600"
          }`}
        >
          {option.label}
        </span>
      </div>
      <p className="text-xs text-gray-400">
        Confidence <span className="text-cyan-400 font-semibold">{(option.confidence * 100).toFixed(1)}%</span>
      </p>
      <div className="text-xs text-gray-400 space-y-1.5 flex-1">
        {Object.entries(option.probabilities)
          .sort((a, b) => b[1] - a[1])
          .map(([k, v]) => (
            <div key={k} className="flex justify-between gap-2 items-center">
              <span className="text-gray-400">{k}</span>
              <div className="flex items-center gap-2 flex-1">
                <div className="flex-1 bg-slate-900/50 rounded-full h-1.5 border border-slate-700">
                  <div 
                    className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full rounded-full"
                    style={{ width: `${v * 100}%` }}
                  />
                </div>
                <span className="text-blue-300 font-semibold w-12 text-right">{(v * 100).toFixed(0)}%</span>
              </div>
            </div>
          ))}
      </div>
      <button
        type="button"
        onClick={onPick}
        disabled={disabled}
        className="mt-auto w-full py-2 text-sm font-medium rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 text-white hover:from-blue-700 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
      >
        This output is better
      </button>
    </div>
  );
}

export default function AbComparePage() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [comparisonId, setComparisonId] = useState<string | null>(null);
  const [left, setLeft] = useState<PairwiseOption | null>(null);
  const [right, setRight] = useState<PairwiseOption | null>(null);
  const [choiceBusy, setChoiceBusy] = useState(false);
  const [thanks, setThanks] = useState<string | null>(null);
  const [stats, setStats] = useState<AbStatsResponse | null>(null);
  const [settings, setSettings] = useState<AbSettingsResponse | null>(null);
  const [toggleBusy, setToggleBusy] = useState(false);

  const loadStats = useCallback(async () => {
    try {
      const s = await api<AbStatsResponse>("/ab/stats");
      setStats(s);
    } catch {
      setStats(null);
    }
  }, []);

  const loadSettings = useCallback(async () => {
    try {
      const s = await api<AbSettingsResponse>("/ab/settings");
      setSettings(s);
    } catch {
      setSettings(null);
    }
  }, []);

  useEffect(() => {
    void loadStats();
    void loadSettings();
  }, [loadStats, loadSettings]);

  const applyToggle = async (enabled: boolean) => {
    setToggleBusy(true);
    setError("");
    try {
      const s = await api<AbSettingsResponse>("/ab/settings", {
        method: "PATCH",
        body: JSON.stringify({ ab_testing_enabled: enabled }),
      });
      setSettings(s);
      await loadStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update settings");
    } finally {
      setToggleBusy(false);
    }
  };

  const runCompare = async (e: React.FormEvent) => {
    e.preventDefault();
    const t = text.trim();
    if (t.length < 10) {
      setError("Text must be at least 10 characters");
      return;
    }
    setLoading(true);
    setError("");
    setThanks(null);
    setComparisonId(null);
    setLeft(null);
    setRight(null);
    try {
      const res = await api<PairwiseCreateResponse>("/ab/pairwise", {
        method: "POST",
        body: JSON.stringify({ text: t }),
      });
      setComparisonId(res.comparison_id);
      setLeft(res.left);
      setRight(res.right);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Comparison failed");
    } finally {
      setLoading(false);
    }
  };

  const submitChoice = async (side: "left" | "right") => {
    if (!comparisonId) return;
    setChoiceBusy(true);
    setError("");
    try {
      await api<{ ok: boolean; chose_model_a: boolean; already_recorded: boolean }>(
        `/ab/pairwise/${comparisonId}/choice`,
        { method: "POST", body: JSON.stringify({ preferred_side: side }) }
      );
      setThanks("Preference saved. Order was randomized — thanks for the pairwise signal.");
      setComparisonId(null);
      setLeft(null);
      setRight(null);
      await loadStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save choice");
    } finally {
      setChoiceBusy(false);
    }
  };

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent mb-2">
          A/B Testing
        </h1>
        <p className="text-gray-400 text-sm mt-2 max-w-3xl">
          Both models classify the same news snippet. Order is randomized to limit position bias. Your choice is recorded and used to update our Bayesian Beta posterior, which probabilistically routes live 
          <code className="text-xs bg-slate-800 border border-slate-700 px-2 py-0.5 rounded text-cyan-300 ml-1">/predict</code> traffic between Model A (primary) and Model B (challenger).
        </p>
      </div>

      {/* A/B Testing Toggle */}
      <div className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl shadow-2xl p-6 backdrop-blur-sm border border-slate-600">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-start gap-3">
            <BarChart3 className="w-6 h-6 text-blue-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-semibold text-gray-200">A/B Testing Status</p>
              <p className="text-xs text-gray-400 mt-1">
                Background job refreshes learned <code className="bg-slate-900/50 px-1 py-0.5 text-cyan-300">p(use A)</code> from pairwise feedback. When off, comparisons are blocked and predictions use Model A only.
              </p>
            </div>
          </div>
          <label className="flex items-center gap-3 cursor-pointer shrink-0">
            <input
              type="checkbox"
              className="rounded border-slate-600 w-5 h-5 accent-blue-500"
              checked={!!settings?.ab_testing_enabled}
              disabled={toggleBusy || settings === null}
              onChange={(e) => void applyToggle(e.target.checked)}
            />
            <span className="text-sm font-medium text-gray-300 min-w-24">
              {settings?.ab_testing_enabled ? (
                <span className="flex items-center gap-1">
                  <CheckCircle className="w-4 h-4 text-green-400" />
                  Enabled
                </span>
              ) : (
                <span className="flex items-center gap-1">
                  <AlertCircle className="w-4 h-4 text-yellow-400" />
                  Disabled
                </span>
              )}
            </span>
          </label>
        </div>
      </div>

      {/* Beta Posterior Info */}
      {settings && (
        <div className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl shadow-2xl p-6 backdrop-blur-sm border border-slate-600">
          <div className="flex items-start gap-3 mb-4">
            <TrendingUp className="w-5 h-5 text-purple-400 mt-0.5 flex-shrink-0" />
            <h3 className="font-semibold text-gray-200">Routing Decision</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700">
              <p className="text-gray-400 text-xs uppercase tracking-wide mb-2">P(Use Model A)</p>
              <p className="text-2xl font-bold text-purple-400">
                {(settings.p_use_model_a * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500 mt-2">
                Beta(α={settings.beta_alpha}, β={settings.beta_beta})
              </p>
            </div>
            <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700">
              <p className="text-gray-400 text-xs uppercase tracking-wide mb-2">Feedback Count</p>
              <p className="text-2xl font-bold text-blue-400">
                {settings.n_completed_feedback}
              </p>
              <p className="text-xs text-gray-500 mt-2">
                {settings.updated_at && `Updated: ${new Date(settings.updated_at).toLocaleTimeString()}`}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Win Statistics */}
      {stats && stats.completed > 0 && (
        <div className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl shadow-2xl p-6 backdrop-blur-sm border border-slate-600">
          <div className="flex items-start gap-3 mb-4">
            <BarChart3 className="w-5 h-5 text-cyan-400 mt-0.5 flex-shrink-0" />
            <h3 className="font-semibold text-gray-200">Aggregate Performance</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700">
              <p className="text-gray-400 text-xs uppercase tracking-wide mb-2">Comparisons</p>
              <p className="text-2xl font-bold text-blue-400">{stats.completed}</p>
            </div>
            <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700">
              <p className="text-gray-400 text-xs uppercase tracking-wide mb-2">Model A Wins</p>
              <p className="text-2xl font-bold text-cyan-400">{stats.wins_a}</p>
              {stats.win_rate_a != null && (
                <p className="text-xs text-gray-400 mt-1">
                  {(stats.win_rate_a * 100).toFixed(1)}%
                  {stats.wilson_low != null && stats.wilson_high != null && (
                    <span> [{(stats.wilson_low * 100).toFixed(1)}%, {(stats.wilson_high * 100).toFixed(1)}%]</span>
                  )}
                </p>
              )}
            </div>
            <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700">
              <p className="text-gray-400 text-xs uppercase tracking-wide mb-2">Model B Wins</p>
              <p className="text-2xl font-bold text-pink-400">{stats.wins_b}</p>
            </div>
          </div>

          {stats.topic_consistency.length > 0 && (
            <div className="pt-4 border-t border-slate-700">
              <p className="text-sm font-medium text-gray-300 mb-3 flex items-center gap-2">
                <Info className="w-4 h-4 text-amber-400" />
                Performance by Topic
              </p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {stats.topic_consistency.slice(0, 8).map((row) => (
                  <div key={row.topic} className="bg-slate-900/50 rounded-lg p-3 border border-slate-700 text-xs">
                    <p className="text-gray-400 font-medium">{row.topic}</p>
                    <p className="text-blue-300 mt-1">A: {(row.win_rate_a * 100).toFixed(0)}%</p>
                    <p className="text-gray-500 text-xs">n={row.n}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Comparison Form */}
      <form onSubmit={runCompare} className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl shadow-2xl p-6 backdrop-blur-sm border border-slate-600 space-y-4">
        <textarea
          className="w-full bg-slate-900/50 border border-slate-600 rounded-xl p-4 h-40 text-sm text-gray-300 placeholder-gray-500 focus:ring-2 focus:ring-cyan-500 focus:outline-none focus:border-cyan-500/50 transition-all resize-none"
          placeholder="Paste a news article to compare models…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={!!settings && !settings.ab_testing_enabled}
        />
        {settings && !settings.ab_testing_enabled && (
          <p className="text-sm text-amber-400 flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            Enable A/B testing above to compare models
          </p>
        )}
        <div className="flex items-center gap-4">
          <button
            type="submit"
            disabled={loading || (settings !== null && !settings.ab_testing_enabled)}
            className="bg-gradient-to-r from-blue-600 to-blue-500 text-white px-6 py-2.5 rounded-lg hover:from-blue-700 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-all flex items-center gap-2"
          >
            <Code className="w-4 h-4" />
            {loading ? "Comparing…" : "Compare Models"}
          </button>
          {error && (
            <span className="text-sm text-red-400 flex items-center gap-1">
              <AlertCircle className="w-4 h-4" />
              {error}
            </span>
          )}
        </div>
      </form>

      {/* Success Message */}
      {thanks && (
        <div className="bg-gradient-to-r from-green-900/30 to-emerald-900/30 border border-green-500/50 text-green-300 text-sm px-4 py-3 rounded-xl flex items-start gap-3">
          <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Preference Recorded</p>
            <p className="text-xs text-green-200 mt-0.5">{thanks}</p>
          </div>
        </div>
      )}

      {/* Comparison Results */}
      {left && right && (
        <div className="space-y-4">
          <p className="text-sm font-medium text-gray-300 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-cyan-400" />
            Which classification is better?
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            <OptionCard
              title="Option 1"
              option={left}
              disabled={choiceBusy}
              onPick={() => void submitChoice("left")}
            />
            <OptionCard
              title="Option 2"
              option={right}
              disabled={choiceBusy}
              onPick={() => void submitChoice("right")}
            />
          </div>
        </div>
      )}

      <p className="text-xs text-gray-500">
        Train a preference head on real labels only:{" "}
        <code className="bg-gray-100 px-1 rounded">GET /api/ab/export</code>, then{" "}
        <code className="bg-gray-100 px-1 rounded">train_preference.py --feedback_file …</code>.
      </p>
    </div>
  );
}
