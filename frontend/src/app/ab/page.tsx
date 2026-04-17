"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type {
  AbSettingsResponse,
  AbStatsResponse,
  PairwiseCreateResponse,
  PairwiseOption,
} from "@/lib/types";

const LABEL_COLORS: Record<string, string> = {
  World: "bg-blue-100 text-blue-800",
  Sports: "bg-green-100 text-green-800",
  Business: "bg-yellow-100 text-yellow-800",
  Technology: "bg-purple-100 text-purple-800",
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
    <div className="border rounded-lg p-4 space-y-3 flex flex-col bg-gray-50/80">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-gray-600">{title}</span>
        <span
          className={`px-2 py-0.5 rounded-full text-xs font-medium ${
            LABEL_COLORS[option.label] || "bg-gray-100 text-gray-800"
          }`}
        >
          {option.label}
        </span>
      </div>
      <p className="text-xs text-gray-500">
        Confidence {(option.confidence * 100).toFixed(1)}%
      </p>
      <div className="text-xs text-gray-600 space-y-1 flex-1">
        {Object.entries(option.probabilities)
          .sort((a, b) => b[1] - a[1])
          .map(([k, v]) => (
            <div key={k} className="flex justify-between gap-2">
              <span>{k}</span>
              <span>{(v * 100).toFixed(1)}%</span>
            </div>
          ))}
      </div>
      <button
        type="button"
        onClick={onPick}
        disabled={disabled}
        className="mt-auto w-full py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
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
      <div>
        <h1 className="text-2xl font-bold">Pairwise A / B</h1>
        <p className="text-gray-600 text-sm mt-2 max-w-3xl">
          Both models classify the same news snippet. Order is randomized to limit position
          bias. Your choice is the label: we update a saved Beta posterior in the background
          and use it to route live <code className="text-xs bg-gray-100 px-1 rounded">/predict</code>{" "}
          traffic between primary (A) and challenger (B). Turn off below to pause collection,
          background refreshes, and probabilistic routing.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p className="font-medium text-gray-800">A/B testing</p>
          <p className="text-xs text-gray-600 mt-1">
            Background job refreshes learned <code className="bg-gray-100 px-1">p(use A)</code> from
            real pairwise feedback only. When off, pairwise compare is blocked and classify uses
            primary only.
          </p>
        </div>
        <label className="flex items-center gap-2 cursor-pointer shrink-0 text-sm">
          <input
            type="checkbox"
            className="rounded border-gray-300 w-5 h-5"
            checked={!!settings?.ab_testing_enabled}
            disabled={toggleBusy || settings === null}
            onChange={(e) => void applyToggle(e.target.checked)}
          />
          <span className="text-gray-800">{settings?.ab_testing_enabled ? "Enabled" : "Disabled"}</span>
        </label>
      </div>

      {settings && (
        <div className="text-sm text-gray-700 bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-1">
          <p>
            Saved routing mean P(next request uses A) ≈{" "}
            <strong>{(settings.p_use_model_a * 100).toFixed(1)}%</strong> (Beta parameters{" "}
            <code className="text-xs bg-white px-1 rounded">
              α={settings.beta_alpha}, β={settings.beta_beta}
            </code>
            , from <strong>{settings.n_completed_feedback}</strong> labeled comparisons).
          </p>
          {settings.updated_at && (
            <p className="text-xs text-gray-500">Last routing update: {settings.updated_at}</p>
          )}
        </div>
      )}

      {stats && stats.completed > 0 && (
        <div className="bg-white rounded-lg shadow p-4 text-sm space-y-2">
          <h2 className="font-semibold text-gray-800">
            Aggregate (model A = primary route, B = configured challenger)
          </h2>
          <p>
            Completed comparisons: <strong>{stats.completed}</strong> — A wins:{" "}
            <strong>{stats.wins_a}</strong>, B wins: <strong>{stats.wins_b}</strong>
            {stats.win_rate_a != null && (
              <>
                {" "}
                → A win rate {(stats.win_rate_a * 100).toFixed(1)}% (Wilson{" "}
                {stats.wilson_low != null && stats.wilson_high != null
                  ? `[${(stats.wilson_low * 100).toFixed(1)}%, ${(stats.wilson_high * 100).toFixed(1)}%]`
                  : ""}
                )
              </>
            )}
          </p>
          <p className="text-gray-600">
            Decision (epsilon on server): <strong>{stats.decision.winner}</strong>
            {stats.decision.n > 0 && stats.decision.p_hat != null && (
              <span className="ml-2">
                (estimated P(A wins) = {(stats.decision.p_hat * 100).toFixed(1)}%)
              </span>
            )}
          </p>
          {stats.topic_consistency.length > 0 && (
            <div className="pt-2 border-t border-gray-100">
              <p className="font-medium text-gray-700 mb-1">Win rate A by topic (model A prediction)</p>
              <ul className="text-xs text-gray-600 space-y-1">
                {stats.topic_consistency.slice(0, 8).map((row) => (
                  <li key={row.topic}>
                    {row.topic}: n={row.n}, A wins {(row.win_rate_a * 100).toFixed(1)}%
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <form className="bg-white rounded-lg shadow p-6 space-y-4">
        <textarea
          className="w-full border rounded-lg p-3 h-36 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
          placeholder="Paste a news article…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={!!settings && !settings.ab_testing_enabled}
        />
        {settings && !settings.ab_testing_enabled && (
          <p className="text-sm text-amber-800">Turn A/B testing on above to collect pairwise feedback.</p>
        )}
        <div className="flex items-center gap-4">
          <button
            type="submit"
            disabled={loading || (settings !== null && !settings.ab_testing_enabled)}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Running both models…" : "Compare"}
          </button>
          {error && <span className="text-sm text-red-600">{error}</span>}
        </div>
      </form>

      {thanks && (
        <div className="bg-green-50 border border-green-200 text-green-800 text-sm px-4 py-3 rounded-lg">
          {thanks}
        </div>
      )}

      {left && right && (
        <div className="space-y-3">
          <p className="text-sm font-medium text-gray-700">
            Which classification is better for this text?
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            <OptionCard
              title="Left"
              option={left}
              disabled={choiceBusy}
              onPick={() => void submitChoice("left")}
            />
            <OptionCard
              title="Right"
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
