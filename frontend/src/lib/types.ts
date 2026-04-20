export interface PredictResponse {
  prediction_id: string | null;
  label: string;
  label_id: number;
  confidence: number;
  probabilities: Record<string, number>;
  explanation: { token: string; score: number }[] | null;
  model_version: string;
  ab_routing_enabled?: boolean;
  ab_served_model?: "a" | "b";
}

export interface PredictionItem {
  id: string;
  text: string;
  predicted_name: string;
  predicted_label: number;
  confidence: number;
  probabilities: Record<string, number>;
  corrected_label: number | null;
  model_version: string;
  created_at: string;
}

export interface DriftReport {
  id: string;
  check_time: string;
  window_start: string;
  window_end: string;
  sample_count: number;
  model_version: string | null;
  label_drift_pvalue: number | null;
  label_drift_detected: boolean;
  confidence_drift_score: number | null;
  confidence_drift_detected: boolean;
  reference_distribution: Record<string, number>;
  current_distribution: Record<string, number>;
  triggered_retraining: boolean;
}

export type DriftLatestByModelResponse = Record<string, DriftReport | null>;

export interface TrainingRun {
  id: string;
  mlflow_run_id: string;
  trigger_reason: string;
  status: string;
  accuracy: number | null;
  f1_macro: number | null;
  previous_f1: number | null;
  deployed: boolean;
  model_uri: string | null;
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
}

export interface ModelInfo {
  version: string;
  loaded: boolean;
  model_name: string;
}

export interface PairwiseOption {
  label: string;
  label_id: number;
  confidence: number;
  probabilities: Record<string, number>;
}

export interface PairwiseCreateResponse {
  comparison_id: string;
  left: PairwiseOption;
  right: PairwiseOption;
}

export interface AbStatsResponse {
  total_comparisons: number;
  completed: number;
  wins_a: number;
  wins_b: number;
  win_rate_a: number | null;
  wilson_low: number | null;
  wilson_high: number | null;
  decision: {
    winner: string;
    p_hat: number | null;
    wilson_low: number | null;
    wilson_high: number | null;
    n: number;
  };
  models: { a: string; b: string };
  topic_consistency: { topic: string; n: number; win_rate_a: number }[];
  ab_testing_enabled: boolean;
  p_use_model_a: number;
  beta_alpha: number;
  beta_beta: number;
  routing_n_completed: number;
  routing_wins_a: number;
  routing_wins_b: number;
  routing_updated_at: string | null;
}

export interface AbSettingsResponse {
  ab_testing_enabled: boolean;
  p_use_model_a: number;
  beta_alpha: number;
  beta_beta: number;
  n_completed_feedback: number;
  wins_a: number;
  wins_b: number;
  updated_at: string | null;
}
