"use client";

import { useEffect } from "react";

/** Last-resort boundary for unexpected rendering errors. */
export default function ErrorPage({ error, reset }: { error: Error; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div role="alert" className="rounded-lg border border-red-200 bg-red-50 p-10 text-center">
      <p className="font-medium text-red-800">Something went wrong while showing this page.</p>
      <button
        type="button"
        onClick={reset}
        className="mt-3 rounded-md bg-red-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-800"
      >
        Try again
      </button>
    </div>
  );
}
