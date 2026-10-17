import { API_BASE_URL } from "@/lib/config";
import type { ErrorEnvelope } from "@/lib/types";

type QueryValue = string | number | boolean | null | undefined;
export type QueryParams = Record<string, QueryValue | readonly QueryValue[]>;

export const NETWORK_ERROR_CODE = "NETWORK_ERROR";
export const UNKNOWN_ERROR_CODE = "UNKNOWN_ERROR";

/** An API failure, carrying the server's error envelope when there is one. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: unknown = null,
    readonly requestId: string | null = null,
    readonly retryAfterSeconds: number | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** Field-level validation messages keyed by field name, e.g. `{ title: "…" }`. */
  fieldErrors(): Record<string, string> {
    if (!Array.isArray(this.details)) return {};
    const errors: Record<string, string> = {};
    for (const detail of this.details) {
      if (detail && typeof detail.field === "string" && typeof detail.message === "string") {
        errors[detail.field] ??= detail.message;
      }
    }
    return errors;
  }
}

export function buildUrl(path: string, query?: QueryParams): string {
  const params = new URLSearchParams();
  for (const [key, raw] of Object.entries(query ?? {})) {
    const values = Array.isArray(raw) ? raw : [raw];
    for (const value of values) {
      if (value !== undefined && value !== null && value !== "") {
        params.append(key, String(value));
      }
    }
  }
  const search = params.toString();
  return `${API_BASE_URL}${path}${search ? `?${search}` : ""}`;
}

function isErrorEnvelope(payload: unknown): payload is ErrorEnvelope {
  return (
    typeof payload === "object" &&
    payload !== null &&
    "error" in payload &&
    typeof (payload as ErrorEnvelope).error?.code === "string"
  );
}

export function toApiError(response: Response, payload: unknown): ApiError {
  const retryAfter = Number.parseInt(response.headers.get("Retry-After") ?? "", 10);
  const retryAfterSeconds = Number.isNaN(retryAfter) ? null : retryAfter;
  const fallbackRequestId = response.headers.get("X-Request-ID");

  if (isErrorEnvelope(payload)) {
    const { code, message, details, request_id } = payload.error;
    return new ApiError(
      response.status,
      code,
      message,
      details ?? null,
      request_id ?? fallbackRequestId,
      retryAfterSeconds,
    );
  }
  return new ApiError(
    response.status,
    UNKNOWN_ERROR_CODE,
    `Request failed with status ${response.status}.`,
    null,
    fallbackRequestId,
    retryAfterSeconds,
  );
}

interface RequestOptions {
  query?: QueryParams;
  body?: unknown;
  signal?: AbortSignal;
}

async function request<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
  const { query, body, signal } = options;
  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      signal,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError(
      0,
      NETWORK_ERROR_CODE,
      "Could not reach the server. Check your connection and try again.",
    );
  }

  if (response.status === 204) return undefined as T;

  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) throw toApiError(response, payload);
  return payload as T;
}

export const http = {
  get: <T>(path: string, query?: QueryParams, signal?: AbortSignal) =>
    request<T>("GET", path, { query, signal }),
  post: <T>(path: string, body: unknown) => request<T>("POST", path, { body }),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, { body }),
  delete: (path: string) => request<void>("DELETE", path),
};
