"use client";

import { useParams } from "next/navigation";

/** The `[id]` route segment as a positive integer, or null if it isn't one. */
export function useIssueId(): number | null {
  const { id } = useParams<{ id: string }>();
  if (!/^\d+$/.test(id)) return null;
  const parsed = Number(id);
  return parsed > 0 && Number.isSafeInteger(parsed) ? parsed : null;
}
