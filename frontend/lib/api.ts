import type { ApiErrorBody, JobRequest, JobResponse } from "./types";

export const API_ORIGIN =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

const JOB_TIMEOUT_MS = 10 * 60 * 1000;

export class ApiError extends Error {
  status: number;
  kind: ApiErrorBody["kind"];
  stage: string | null;
  hint: string | null;

  constructor(status: number, body: Partial<ApiErrorBody> & { message: string }) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.kind = body.kind ?? "internal";
    this.stage = body.stage ?? null;
    this.hint = body.hint ?? null;
  }
}

async function request<T>(path: string, init: RequestInit, timeoutMs: number): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${API_ORIGIN}${path}`, {
      headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
      signal: controller.signal,
      ...init,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new ApiError(408, {
        kind: "upstream",
        message: `The request timed out after ${Math.round(timeoutMs / 60000)} minutes.`,
        hint: "The pipeline may still be running. Try fewer organisms.",
      });
    }
    throw new ApiError(0, {
      kind: "upstream",
      message: "Could not reach the OrthoScope API.",
      hint: `Check that the backend is running at ${API_ORIGIN}.`,
    });
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    let body: Partial<ApiErrorBody> & { message: string } = {
      message: res.statusText || `Request failed with status ${res.status}`,
    };
    try {
      const parsed = await res.json();
      if (parsed?.error?.message) {
        body = parsed.error;
      } else if (parsed?.detail) {
        body = {
          kind: "invalid_input",
          message:
            typeof parsed.detail === "string"
              ? parsed.detail
              : JSON.stringify(parsed.detail),
        };
      }
    } catch {}
    throw new ApiError(res.status, body);
  }

  return res.json() as Promise<T>;
}

export function createJob(req: JobRequest): Promise<JobResponse> {
  return request<JobResponse>(
    "/jobs",
    { method: "POST", body: JSON.stringify(req) },
    JOB_TIMEOUT_MS
  );
}

export function fileUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (/^https?:\/\//.test(path)) return path;
  return `${API_ORIGIN}${path}`;
}
