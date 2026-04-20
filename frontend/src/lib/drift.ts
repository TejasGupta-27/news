import { DriftReport } from "@/lib/types";

export function normalizeModelVersion(modelVersion: string | null | undefined): string {
  return modelVersion || "unknown";
}

export function isModelB(modelVersion: string | null | undefined): boolean {
  const normalized = normalizeModelVersion(modelVersion);
  // Check for both "ab-b:" prefix (legacy) and "new-khabar-b" (current)
  return normalized.startsWith("ab-b:") || normalized.includes("new-khabar-b");
}

export function getModelLabel(modelVersion: string | null | undefined): string {
  const normalized = normalizeModelVersion(modelVersion);
  if (normalized === "unknown") {
    return "Unknown Model";
  }
  return isModelB(modelVersion) ? "Model B" : "Model A";
}

export function hasDrift(report: DriftReport | null | undefined): boolean {
  return !!report && (report.label_drift_detected || report.confidence_drift_detected);
}

export function sortModelVersions(versions: string[]): string[] {
  return [...versions].sort((a, b) => {
    const rank = (value: string) => {
      if (value === "unknown") return 2;
      return value.startsWith("ab-b:") ? 1 : 0;
    };

    const rankDiff = rank(a) - rank(b);
    if (rankDiff !== 0) return rankDiff;
    return a.localeCompare(b);
  });
}

export function groupReportsByModel(reports: DriftReport[]): Record<string, DriftReport[]> {
  const grouped: Record<string, DriftReport[]> = {};

  for (const report of reports) {
    const modelVersion = normalizeModelVersion(report.model_version);
    if (!grouped[modelVersion]) grouped[modelVersion] = [];
    grouped[modelVersion].push(report);
  }

  for (const version of Object.keys(grouped)) {
    grouped[version] = [...grouped[version]].sort(
      (a, b) => new Date(a.check_time).getTime() - new Date(b.check_time).getTime()
    );
  }

  return grouped;
}

export function getLatestReportsByModel(reports: DriftReport[]): Record<string, DriftReport> {
  const latest: Record<string, DriftReport> = {};

  for (const report of reports) {
    const modelVersion = normalizeModelVersion(report.model_version);
    const current = latest[modelVersion];

    if (
      !current ||
      new Date(report.check_time).getTime() > new Date(current.check_time).getTime()
    ) {
      latest[modelVersion] = report;
    }
  }

  return latest;
}
