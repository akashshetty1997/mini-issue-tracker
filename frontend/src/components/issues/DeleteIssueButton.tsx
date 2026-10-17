"use client";

import { useState } from "react";

interface DeleteIssueButtonProps {
  deleting: boolean;
  onConfirm: () => void;
}

/** Two-step delete: the first click asks for confirmation instead of deleting. */
export function DeleteIssueButton({ deleting, onConfirm }: DeleteIssueButtonProps) {
  const [confirming, setConfirming] = useState(false);

  if (!confirming) {
    return (
      <button
        type="button"
        onClick={() => setConfirming(true)}
        className="rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50"
      >
        Delete
      </button>
    );
  }

  return (
    <div role="group" aria-label="Confirm delete" className="flex items-center gap-2 text-sm">
      <span className="text-zinc-700">Delete permanently?</span>
      <button
        type="button"
        disabled={deleting}
        onClick={onConfirm}
        className="rounded-md bg-red-600 px-3 py-1.5 font-medium text-white hover:bg-red-700 disabled:opacity-60"
      >
        {deleting ? "Deleting…" : "Yes, delete"}
      </button>
      <button
        type="button"
        disabled={deleting}
        onClick={() => setConfirming(false)}
        className="rounded-md border border-zinc-300 bg-white px-3 py-1.5 font-medium hover:bg-zinc-50"
      >
        Cancel
      </button>
    </div>
  );
}
