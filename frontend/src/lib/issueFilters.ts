/**
 * Issue list filters <-> URL query string <-> API query.
 *
 * Filters live in the URL so a filtered view can be shared, bookmarked and survives a
 * reload. These functions are pure so they can be unit-tested without a router.
 */
import { DEFAULT_SORT, PRIORITIES, SORT_OPTIONS, STATUSES } from "@/lib/constants";
import type { IssueListQuery, IssuePriority, IssueStatus } from "@/lib/types";

export interface IssueFilterState {
  status: IssueStatus[];
  priority: IssuePriority[];
  assigneeId: number | null;
  q: string;
  sort: string;
  page: number;
}

export const DEFAULT_FILTERS: IssueFilterState = {
  status: [],
  priority: [],
  assigneeId: null,
  q: "",
  sort: DEFAULT_SORT,
  page: 1,
};

interface ReadableParams {
  get(name: string): string | null;
  getAll(name: string): string[];
}

const SORT_VALUES: readonly string[] = SORT_OPTIONS.map((option) => option.value);

function oneOf<T extends string>(allowed: readonly T[], values: string[]): T[] {
  const valid = values.filter((value): value is T => (allowed as readonly string[]).includes(value));
  return [...new Set(valid)];
}

function positiveInt(value: string | null): number | null {
  if (value === null || !/^\d+$/.test(value)) return null;
  const parsed = Number(value);
  return parsed > 0 && Number.isSafeInteger(parsed) ? parsed : null;
}

/** Read filters from the URL, silently dropping anything malformed. */
export function parseFilters(params: ReadableParams): IssueFilterState {
  const sort = params.get("sort");
  return {
    status: oneOf(STATUSES, params.getAll("status")),
    priority: oneOf(PRIORITIES, params.getAll("priority")),
    assigneeId: positiveInt(params.get("assignee")),
    q: params.get("q") ?? "",
    sort: sort !== null && SORT_VALUES.includes(sort) ? sort : DEFAULT_SORT,
    page: positiveInt(params.get("page")) ?? 1,
  };
}

/** Write filters to a query string, omitting defaults to keep URLs short. */
export function toSearchParams(filters: IssueFilterState): URLSearchParams {
  const params = new URLSearchParams();
  filters.status.forEach((status) => params.append("status", status));
  filters.priority.forEach((priority) => params.append("priority", priority));
  if (filters.assigneeId !== null) params.set("assignee", String(filters.assigneeId));
  if (filters.q.trim()) params.set("q", filters.q.trim());
  if (filters.sort !== DEFAULT_SORT) params.set("sort", filters.sort);
  if (filters.page > 1) params.set("page", String(filters.page));
  return params;
}

export function toListQuery(filters: IssueFilterState, pageSize: number): IssueListQuery {
  return {
    status: filters.status.length ? filters.status : undefined,
    priority: filters.priority.length ? filters.priority : undefined,
    assignee_id: filters.assigneeId ?? undefined,
    q: filters.q.trim() || undefined,
    sort: filters.sort,
    limit: pageSize,
    offset: (filters.page - 1) * pageSize,
  };
}

export function hasActiveFilters(filters: IssueFilterState): boolean {
  return (
    filters.status.length > 0 ||
    filters.priority.length > 0 ||
    filters.assigneeId !== null ||
    filters.q.trim() !== ""
  );
}
