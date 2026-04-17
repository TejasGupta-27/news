"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { PredictResponse } from "@/lib/types";
import ConfidenceBar from "@/components/ConfidenceBar";
import ExplanationChart from "@/components/ExplanationChart";
import FeedbackWidget from "@/components/FeedbackWidget";

const LABEL_COLORS: Record<string, string> = {
  World: "bg-blue-100 text-blue-800",
  Sports: "bg-green-100 text-green-800",
  Business: "bg-yellow-100 text-yellow-800",
  Technology: "bg-purple-100 text-purple-800",
};

export default function PredictPage() {
  const [text, setText] = useState("");
  const [explain, setExplain] = useState(false);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim().length < 10) {
      setError("Text must be at least 10 characters");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await api<PredictResponse>("/predict", {
        method: "POST",
        body: JSON.stringify({ text, explain }),
      });
      setResult(res);
      setError("");
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Unknown error";
      console.error("Prediction error:", errorMsg);
      setError(
        "Classification failed. Please check if the backend is running and try again."
      );
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleExplain = (checked: boolean) => {
    setExplain(checked);
    // Clear result when toggling explanation to prompt re-prediction
    if (result) {
      setResult(null);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Classify Article</h1>

      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-4">
        <textarea
          className="w-full border rounded-lg p-3 h-40 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
          placeholder="Paste a news article here..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={explain}
              onChange={(e) => handleToggleExplain(e.target.checked)}
              className="rounded cursor-pointer w-4 h-4"
            />
            <span className="flex items-center gap-1">
              Include explanations
              {explain && <span className="text-xs text-amber-600">(slower)</span>}
            </span>
          </label>
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="animate-spin">⏳</span>
                {explain ? "Classifying with explanations..." : "Classifying..."}
              </span>
            ) : (
              "Classify"
            )}
          </button>
        </div>
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}
      </form>

      {result && (
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <div className="flex items-center gap-4">
            <span className="text-lg font-semibold">Predicted Topic:</span>
            <span
              className={`px-4 py-1 rounded-full text-sm font-medium ${
                LABEL_COLORS[result.label] || "bg-gray-100"
              }`}
            >
              {result.label}
            </span>
            <span className="text-gray-500 text-sm">
              Confidence: {(result.confidence * 100).toFixed(1)}%
            </span>
          </div>

          <ConfidenceBar probabilities={result.probabilities} />

          <p className="text-xs text-gray-400">Model: {result.model_version}</p>
          {result.ab_routing_enabled && (
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1.5 inline-block">
              A/B routing on — this request used checkpoint{" "}
              <strong>{result.ab_served_model === "b" ? "B (challenger)" : "A (primary)"}</strong>
              .
            </p>
          )}

          {result.explanation && result.explanation.length > 0 ? (
            <ExplanationChart explanation={result.explanation} />
          ) : explain ? (
            <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-lg text-sm">
              Explanations were requested but could not be generated. Showing basic classification only.
            </div>
          ) : null}

          {result.prediction_id && (
            <FeedbackWidget
              predictionId={result.prediction_id}
              predictedLabelId={result.label_id}
            />
          )}
        </div>
      )}
    </div>
  );
}
