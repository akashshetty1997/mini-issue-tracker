"use client";

import { SearchInput } from "@/components/issues/SearchInput";
import {
  PRIORITIES,
  PRIORITY_LABELS,
  SORT_OPTIONS,
  STATUSES,
  STATUS_LABELS,
} from "@/lib/constants";
import { hasActiveFilters, type IssueFilterState } from "@/lib/issueFilters";
import type { User } from "@/lib/types";

interface IssueFiltersProps {
  filters: IssueFilterState;
  users: User[];
  onChange: (patch: Partial<IssueFilterState>) => void;
  onReset: () => void;
}

const SELECT =
  "rounded-md border border-zinc-300 bg-white px-2 py-2 text-sm shadow-sm focus:border-zinc-500 focus:outline-none";

function toggle<T>(values: T[], value: T): T[] {
  return values.includes(value) ? values.filter((v) => v !== value) : [...values, value];
}

function Chip({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
        active
          ? "border-zinc-900 bg-zinc-900 text-white"
          : "border-zinc-300 bg-white text-zinc-700 hover:bg-zinc-100"
      }`}
    >
      {label}
    </button>
  );
}

export function IssueFilters({ filters, users, onChange, onReset }: IssueFiltersProps) {
  return (
    <section aria-label="Filters" className="space-y-3 rounded-lg border border-zinc-200 bg-white p-4">
      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="flex-1">
          <SearchInput value={filters.q} onSearch={(q) => onChange({ q })} />
        </div>
        <select
          aria-label="Assignee"
          className={SELECT}
          value={filters.assigneeId ?? ""}
          onChange={(e) => onChange({ assigneeId: e.target.value ? Number(e.target.value) : null })}
        >
          <option value="">Any assignee</option>
          {users.map((user) => (
            <option key={user.id} value={user.id}>
              {user.name}
            </option>
          ))}
        </select>
        <select
          aria-label="Sort by"
          className={SELECT}
          value={filters.sort}
          onChange={(e) => onChange({ sort: e.target.value })}
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <fieldset className="flex flex-wrap items-center gap-2">
          <legend className="sr-only">Status</legend>
          <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">Status</span>
          {STATUSES.map((status) => (
            <Chip
              key={status}
              label={STATUS_LABELS[status]}
              active={filters.status.includes(status)}
              onClick={() => onChange({ status: toggle(filters.status, status) })}
            />
          ))}
        </fieldset>
        <fieldset className="flex flex-wrap items-center gap-2">
          <legend className="sr-only">Priority</legend>
          <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">
            Priority
          </span>
          {PRIORITIES.map((priority) => (
            <Chip
              key={priority}
              label={PRIORITY_LABELS[priority]}
              active={filters.priority.includes(priority)}
              onClick={() => onChange({ priority: toggle(filters.priority, priority) })}
            />
          ))}
        </fieldset>
        {hasActiveFilters(filters) && (
          <button
            type="button"
            onClick={onReset}
            className="text-sm font-medium text-zinc-600 underline underline-offset-2 hover:text-zinc-900"
          >
            Clear filters
          </button>
        )}
      </div>
    </section>
  );
}
