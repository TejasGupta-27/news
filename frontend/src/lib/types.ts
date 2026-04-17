export interface PredictResponse {
  prediction_id: string | null;
  label: string;
  label_id: number;
  confidence: number;
  probabilities: Record<string, number>;
  explanation: { token: string; score: number }[] | null;
  model_version: string;
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
  label_drift_pvalue: number | null;
  label_drift_detected: boolean;
  confidence_drift_score: number | null;
  confidence_drift_detected: boolean;
  reference_distribution: Record<string, number>;
  current_distribution: Record<string, number>;
  triggered_retraining: boolean;
}

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
