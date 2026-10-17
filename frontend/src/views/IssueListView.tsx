"use client";

import Link from "next/link";

import { IssueFilters } from "@/components/issues/IssueFilters";
import { IssueTable } from "@/components/issues/IssueTable";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Pagination } from "@/components/ui/Pagination";
import { useIssueList, useUsers } from "@/hooks/queries";
import { useIssueFilters } from "@/hooks/useIssueFilters";
import { PAGE_SIZE, ROUTES } from "@/lib/constants";
import { hasActiveFilters, toListQuery } from "@/lib/issueFilters";

export function IssueListView() {
  const { filters, setFilters, resetFilters } = useIssueFilters();
  const issues = useIssueList(toListQuery(filters, PAGE_SIZE));
  const users = useUsers();

  return (
    <div className="space-y-4">
      <IssueFilters
        filters={filters}
        users={users.data ?? []}
        onChange={setFilters}
        onReset={resetFilters}
      />

      {issues.isError && <ErrorBanner error={issues.error} onRetry={() => issues.refetch()} />}

      {issues.isPending && <ListSkeleton />}

      {issues.data && (
        <div className={`space-y-4 ${issues.isPlaceholderData ? "opacity-60" : ""}`}>
          {issues.data.items.length > 0 ? (
            <IssueTable issues={issues.data.items} />
          ) : (
            <EmptyState
              filtered={hasActiveFilters(filters) || filters.page > 1}
              onReset={resetFilters}
            />
          )}
          <Pagination
            page={filters.page}
            pageSize={PAGE_SIZE}
            total={issues.data.total}
            onPageChange={(page) => setFilters({ page })}
          />
        </div>
      )}
    </div>
  );
}

function EmptyState({ filtered, onReset }: { filtered: boolean; onReset: () => void }) {
  return (
    <div className="rounded-lg border border-dashed border-zinc-300 bg-white p-10 text-center">
      {filtered ? (
        <>
          <p className="font-medium">No issues match these filters.</p>
          <button
            type="button"
            onClick={onReset}
            className="mt-2 text-sm text-zinc-600 underline underline-offset-2"
          >
            Clear filters
          </button>
        </>
      ) : (
        <>
          <p className="font-medium">No issues yet.</p>
          <Link
            href={ROUTES.newIssue}
            className="mt-2 inline-block text-sm text-zinc-600 underline underline-offset-2"
          >
            Create the first one
          </Link>
        </>
      )}
    </div>
  );
}

export function ListSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading issues" className="space-y-2">
      {Array.from({ length: 5 }, (_, i) => (
        <div key={i} className="h-12 animate-pulse rounded-md bg-zinc-200/70" />
      ))}
    </div>
  );
}
