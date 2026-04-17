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
    } catch (err) {
      setError("Classification failed. Is the backend running?");
    } finally {
      setLoading(false);
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
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={explain}
              onChange={(e) => setExplain(e.target.checked)}
              className="rounded"
            />
            Include explanations (slower)
          </label>
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Classifying..." : "Classify"}
          </button>
        </div>
        {error && <p className="text-red-500 text-sm">{error}</p>}
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

          {result.explanation && <ExplanationChart explanation={result.explanation} />}

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
