import { ApiError } from "@/lib/api/client";

/** A user-facing sentence for any error thrown by the API layer. */
export function describeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 429) {
      return error.retryAfterSeconds
        ? `Too many requests. Please retry in ${error.retryAfterSeconds}s.`
        : "Too many requests. Please wait a moment and retry.";
    }
    if (isVersionConflict(error)) {
      return "Someone else changed this issue while you were viewing it. The latest version has been loaded; please review it and try again.";
    }
    return error.message;
  }
  return "Something went wrong. Please try again.";
}

export function isVersionConflict(error: unknown): boolean {
  return error instanceof ApiError && error.code === "VERSION_CONFLICT";
}

export function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}
