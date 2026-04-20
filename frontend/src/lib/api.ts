export const API_URL = "/api";

export async function readErrorDetail(res: Response, fallback: string): Promise<string> {
  const contentType = res.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    try {
      const errorData = (await res.json()) as { detail?: unknown };
      if (typeof errorData.detail === "string") {
        return errorData.detail;
      }
      if (Array.isArray(errorData.detail)) {
        return errorData.detail
          .map((item) =>
            typeof item === "object" && item && "msg" in item
              ? String((item as { msg: unknown }).msg)
              : String(item)
          )
          .join(", ");
      }
    } catch {
      return fallback;
    }
  }

  try {
    const text = await res.text();
    if (text && !text.trimStart().startsWith("<")) {
      return text.slice(0, 200);
    }
  } catch {
    return fallback;
  }

  return fallback;
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  try {
    const headers = new Headers(options?.headers);
    if (!(options?.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }

    const res = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      throw new Error(await readErrorDetail(res, `API error: ${res.status}`));
    }

    return res.json();
  } catch (error) {
    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw new Error("Could not connect to API. Is the backend running?");
    }
    throw error;
  }
}

export const fetcher = <T>(path: string) => api<T>(path);

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/health`, {
      method: "GET",
    });
    return res.ok;
  } catch {
    return false;
  }
}
