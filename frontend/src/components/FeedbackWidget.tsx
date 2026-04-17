"use client";
import { useState } from "react";
import { api } from "@/lib/api";

const LABELS = ["World", "Sports", "Business", "Technology"];

interface Props {
  predictionId: string;
  predictedLabelId: number;
}

type Status = "idle" | "correct" | "picking" | "submitting" | "saved" | "error";

export default function FeedbackWidget({ predictionId, predictedLabelId }: Props) {
  const [status, setStatus] = useState<Status>("idle");
  const [chosen, setChosen] = useState<number | null>(null);
  const [error, setError] = useState("");

  const markCorrect = async () => {
    setStatus("submitting");
    setError("");
    try {
      await api(`/predictions/${predictionId}/correct`, {
        method: "PATCH",
        body: JSON.stringify({ corrected_label: predictedLabelId }),
      });
      setStatus("correct");
    } catch (e) {
      setError("Failed to save feedback");
      setStatus("error");
    }
  };

  const submitCorrection = async (labelId: number) => {
    setStatus("submitting");
    setError("");
    setChosen(labelId);
    try {
      await api(`/predictions/${predictionId}/correct`, {
        method: "PATCH",
        body: JSON.stringify({ corrected_label: labelId }),
      });
      setStatus("saved");
    } catch (e) {
      setError("Failed to save feedback");
      setStatus("error");
    }
  };

  if (status === "correct") {
    return (
      <div className="text-sm text-green-700 bg-green-50 px-3 py-2 rounded">
        Thanks — recorded as correct. This will reinforce the model on the next retrain.
      </div>
    );
  }

  if (status === "saved") {
    return (
      <div className="text-sm text-blue-700 bg-blue-50 px-3 py-2 rounded">
        Thanks — saved as <strong>{LABELS[chosen!]}</strong>. The retraining pipeline will learn from this correction.
      </div>
    );
  }

  if (status === "picking") {
    return (
      <div className="border-t pt-3 space-y-2">
        <p className="text-sm text-gray-700">Which label is correct?</p>
        <div className="flex flex-wrap gap-2">
          {LABELS.map((name, id) => (
            <button
              key={id}
              onClick={() => submitCorrection(id)}
              disabled={id === predictedLabelId}
              className="px-3 py-1 text-sm border rounded hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {name}
            </button>
          ))}
          <button
            onClick={() => setStatus("idle")}
            className="px-3 py-1 text-sm text-gray-500 hover:text-gray-700"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="border-t pt-3 flex items-center gap-3">
      <span className="text-sm text-gray-600">Was this prediction correct?</span>
      <button
        onClick={markCorrect}
        disabled={status === "submitting"}
        className="px-3 py-1 text-sm bg-green-50 hover:bg-green-100 text-green-700 border border-green-200 rounded"
      >
        Yes
      </button>
      <button
        onClick={() => setStatus("picking")}
        disabled={status === "submitting"}
        className="px-3 py-1 text-sm bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 rounded"
      >
        No
      </button>
      {error && <span className="text-xs text-red-500">{error}</span>}
    </div>
  );
}
