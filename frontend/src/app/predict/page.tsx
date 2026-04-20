"use client";
import { useState } from "react";
import { api, API_URL, readErrorDetail } from "@/lib/api";
import { PredictResponse } from "@/lib/types";
import ConfidenceBar from "@/components/ConfidenceBar";
import ExplanationChart from "@/components/ExplanationChart";
import FeedbackWidget from "@/components/FeedbackWidget";
import { AlertTriangle, Sparkles, Zap } from "lucide-react";

const LABEL_COLORS: Record<string, string> = {
  World: "bg-gradient-to-br from-blue-500 to-cyan-500 text-white",
  Sports: "bg-gradient-to-br from-green-500 to-emerald-500 text-white",
  Business: "bg-gradient-to-br from-amber-500 to-orange-500 text-white",
  Technology: "bg-gradient-to-br from-purple-500 to-indigo-500 text-white",
};

type InputMode = "text" | "file";

export default function PredictPage() {
  const [inputMode, setInputMode] = useState<InputMode>("text");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [explain, setExplain] = useState(false);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [cacheHit, setCacheHit] = useState(false);

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    setError("");
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      const ext = selectedFile.name.split(".").pop()?.toLowerCase();
      if (!["txt", "pdf", "docx"].includes(ext || "")) {
        setError("Unsupported file format. Please use .txt, .pdf, or .docx");
        setFile(null);
        return;
      }
      setFile(selectedFile);
      setError("");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setCacheHit(false);

    // Validation
    if (inputMode === "text") {
      if (text.trim().length < 10) {
        setError("Text must be at least 10 characters");
        return;
      }
    } else {
      if (!file) {
        setError("Please select a file");
        return;
      }
    }

    setLoading(true);
    try {
      let res: PredictResponse;

      if (inputMode === "text") {
        res = await api<PredictResponse>("/predict", {
          method: "POST",
          body: JSON.stringify({ text, explain }),
        });
      } else {
        // File upload
        const formData = new FormData();
        formData.append("file", file!);
        formData.append("explain", String(explain));

        const response = await fetch(`${API_URL}/predict/file`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          throw new Error(await readErrorDetail(response, "File prediction failed"));
        }
        res = await response.json();
      }

      setResult(res);
      setCacheHit(res.model_version?.includes("cache") || false);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Unknown error";
      console.error("Prediction error:", errorMsg);
      setError(errorMsg || "Classification failed. Please try again.");
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleExplain = (checked: boolean) => {
    setExplain(checked);
    if (result) {
      setResult(null);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent mb-2">
            Article Classifier
          </h1>
          <p className="text-gray-300">
            Classify your news articles across World, Sports, Business, and Technology topics
          </p>
        </div>

        {/* Input Mode Selector */}
        <div className="mb-8 flex gap-2 bg-slate-800 rounded-lg p-1 w-fit">
          <button
            onClick={() => {
              setInputMode("text");
              setFile(null);
              setError("");
            }}
            className={`px-6 py-2 rounded-md font-medium transition-all ${
              inputMode === "text"
                ? "bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-lg"
                : "text-gray-300 hover:text-white"
            }`}
          >
            📝 Paste Text
          </button>
          <button
            onClick={() => {
              setInputMode("file");
              setText("");
              setError("");
            }}
            className={`px-6 py-2 rounded-md font-medium transition-all ${
              inputMode === "file"
                ? "bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-lg"
                : "text-gray-300 hover:text-white"
            }`}
          >
            📄 Upload File
          </button>
        </div>

        {/* Main Input Form */}
        <form onSubmit={handleSubmit} className="mb-8">
          <div className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl shadow-2xl p-8 backdrop-blur-sm border border-slate-600">
            {inputMode === "text" ? (
              <div className="space-y-4">
                <label className="block text-sm font-medium text-gray-200">
                  Paste your article here
                </label>
                <textarea
                  className="w-full h-64 bg-slate-900 border border-slate-600 rounded-xl p-4 text-gray-100 placeholder-gray-500 focus:ring-2 focus:ring-cyan-500 focus:border-transparent resize-none transition-all"
                  placeholder="Enter a news article or any text you want to classify..."
                  value={text}
                  onChange={handleTextChange}
                />
                <p className="text-xs text-gray-400">
                  {text.length} characters • Minimum 10 required
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <label className="block text-sm font-medium text-gray-200">
                  Upload a document
                </label>
                <div className="border-2 border-dashed border-slate-600 rounded-xl p-8 text-center hover:border-cyan-500 transition-colors">
                  <input
                    type="file"
                    accept=".txt,.pdf,.docx"
                    onChange={handleFileChange}
                    className="hidden"
                    id="file-input"
                  />
                  <label
                    htmlFor="file-input"
                    className="cursor-pointer block space-y-2"
                  >
                    <div className="text-4xl">📁</div>
                    <div className="text-gray-300 font-medium">
                      {file ? file.name : "Click to select or drag & drop"}
                    </div>
                    <div className="text-xs text-gray-500">
                      Supported: .txt, .pdf, .docx
                    </div>
                  </label>
                </div>
              </div>
            )}

            {/* Options and Submit */}
            <div className="mt-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <label className="flex items-center gap-3 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={explain}
                  onChange={(e) => handleToggleExplain(e.target.checked)}
                  className="w-5 h-5 rounded accent-cyan-500"
                />
                <span className="text-sm text-gray-300 group-hover:text-gray-200">
                  Include explanations
                  {explain && (
                    <span className="text-xs text-amber-400 ml-2">(may be slower)</span>
                  )}
                </span>
              </label>

              <button
                type="submit"
                disabled={loading}
                className="bg-gradient-to-r from-cyan-500 to-blue-500 text-white font-semibold px-8 py-3 rounded-xl hover:shadow-lg hover:shadow-cyan-500/50 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
              >
                {loading ? (
                  <>
                    <span className="animate-spin">⌛</span>
                    {explain ? "Classifying..." : "Classifying..."}
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Classify
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mt-4 bg-red-900/30 border border-red-500/50 text-red-200 px-6 py-4 rounded-xl text-sm backdrop-blur-sm flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}
        </form>

        {/* Result Display */}
        {result && (
          <div className="space-y-6 animate-fadeIn">
            {/* Main Result Card */}
            <div className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl shadow-2xl p-8 backdrop-blur-sm border border-slate-600">
              <div className="space-y-6">
                {/* Prediction Result */}
                <div className="space-y-3">
                  <p className="text-sm font-medium text-gray-400 uppercase tracking-wide">
                    Classification Result
                  </p>
                  <div className={`inline-block px-6 py-3 rounded-xl font-bold text-lg ${LABEL_COLORS[result.label] || "bg-slate-600"}`}>
                    {result.label}
                  </div>
                </div>

                {/* Confidence Display */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-gray-400">Confidence Score</p>
                    <p className="text-xl font-bold text-cyan-400">
                      {(result.confidence * 100).toFixed(1)}%
                    </p>
                  </div>
                  <div className="w-full bg-slate-900 rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-cyan-500 to-blue-500 h-full rounded-full transition-all"
                      style={{ width: `${result.confidence * 100}%` }}
                    />
                  </div>
                </div>

                {/* Model & Cache Info */}
                <div className="flex flex-wrap items-center gap-3 text-xs text-gray-400">
                  <span className="font-mono">Model: {result.model_version}</span>
                  {cacheHit && (
                    <span className="bg-green-500/20 text-green-400 px-2.5 py-1.5 rounded-full flex items-center gap-1.5">
                      <Zap className="w-3 h-3" />
                      Cache Hit
                    </span>
                  )}
                  {result.ab_routing_enabled && (
                    <span className="bg-amber-500/20 text-amber-300 px-2.5 py-1.5 rounded-full">
                      A/B: {result.ab_served_model === "b" ? "Model B" : "Model A"}
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Probability Distribution */}
            <div className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl shadow-2xl p-8 backdrop-blur-sm border border-slate-600">
              <ConfidenceBar probabilities={result.probabilities} />
            </div>

            {/* Explanations */}
            {result.explanation && result.explanation.length > 0 && (
              <div className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl shadow-2xl p-8 backdrop-blur-sm border border-slate-600">
                <ExplanationChart explanation={result.explanation} />
              </div>
            )}

            {explain && !result.explanation && (
              <div className="bg-yellow-900/30 border border-yellow-500/50 text-yellow-200 px-6 py-4 rounded-xl text-sm backdrop-blur-sm flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <span>Explanations were requested but could not be generated. Showing basic classification only.</span>
              </div>
            )}

            {/* Feedback Widget */}
            {result.prediction_id && (
              <div className="bg-gradient-to-br from-slate-800 to-slate-700 rounded-2xl shadow-2xl p-8 backdrop-blur-sm border border-slate-600">
                <FeedbackWidget
                  predictionId={result.prediction_id}
                  predictedLabelId={result.label_id}
                />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Animation */}
      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}
