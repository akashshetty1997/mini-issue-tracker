/**
 * UI constants. Domain rules (statuses, transitions, field limits) come from the API:
 * types from the generated OpenAPI schema, runtime values from GET /api/v1/meta.
 */
import type { IssuePriority, IssueStatus } from "@/lib/types";

export const API_V1_PREFIX = "/api/v1";

// `Record<IssueStatus, …>` must list every status, so if the backend adds one,
// `npm run gen:api` makes this file fail to type-check until it gets a label.
export const STATUS_LABELS: Record<IssueStatus, string> = {
  open: "Open",
  in_progress: "In progress",
  resolved: "Resolved",
  closed: "Closed",
};

export const PRIORITY_LABELS: Record<IssuePriority, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

export const STATUSES = Object.keys(STATUS_LABELS) as IssueStatus[];
export const PRIORITIES = Object.keys(PRIORITY_LABELS) as IssuePriority[];

export const STATUS_BADGE_CLASSES: Record<IssueStatus, string> = {
  open: "bg-sky-50 text-sky-800 ring-sky-600/20",
  in_progress: "bg-amber-50 text-amber-800 ring-amber-600/20",
  resolved: "bg-emerald-50 text-emerald-800 ring-emerald-600/20",
  closed: "bg-zinc-100 text-zinc-700 ring-zinc-500/20",
};

export const PRIORITY_BADGE_CLASSES: Record<IssuePriority, string> = {
  low: "bg-zinc-50 text-zinc-600 ring-zinc-500/20",
  medium: "bg-indigo-50 text-indigo-700 ring-indigo-600/20",
  high: "bg-orange-50 text-orange-800 ring-orange-600/20",
  critical: "bg-red-50 text-red-700 ring-red-600/30",
};

export const SORT_OPTIONS = [
  { value: "-created_at", label: "Newest first" },
  { value: "created_at", label: "Oldest first" },
  { value: "-updated_at", label: "Recently updated" },
  { value: "-priority", label: "Highest priority" },
  { value: "priority", label: "Lowest priority" },
  { value: "title", label: "Title A–Z" },
] as const;

export const DEFAULT_SORT = "-created_at";
export const PAGE_SIZE = 20;
export const SEARCH_DEBOUNCE_MS = 300;
// How long fetched data is considered fresh before a background refetch.
export const QUERY_STALE_TIME_MS = 15_000;

export const ROUTES = {
  issues: "/",
  newIssue: "/issues/new",
  issue: (id: number) => `/issues/${id}`,
  editIssue: (id: number) => `/issues/${id}/edit`,
} as const;
