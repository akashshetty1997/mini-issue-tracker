import { ApiError } from "@/lib/api/client";
import { describeError } from "@/lib/errors";

interface ErrorBannerProps {
  error: unknown;
  onRetry?: () => void;
}

export function ErrorBanner({ error, onRetry }: ErrorBannerProps) {
  const requestId = error instanceof ApiError ? error.requestId : null;
  return (
    <div role="alert" className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-800">
      <div className="flex items-start justify-between gap-4">
        <p>{describeError(error)}</p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="shrink-0 font-medium underline underline-offset-2 hover:text-red-950"
          >
            Retry
          </button>
        )}
      </div>
      {requestId && <p className="mt-1 text-xs text-red-600">Reference: {requestId}</p>}
    </div>
  );
}
