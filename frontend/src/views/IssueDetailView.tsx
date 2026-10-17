"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { DeleteIssueButton } from "@/components/issues/DeleteIssueButton";
import { PriorityBadge, StatusBadge } from "@/components/issues/Badges";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { NotFoundPanel } from "@/components/ui/NotFoundPanel";
import { useDeleteIssue, useIssue, useUpdateIssue, useUsers } from "@/hooks/queries";
import { useIssueId } from "@/hooks/useIssueId";
import { ROUTES, STATUS_LABELS } from "@/lib/constants";
import { isNotFound } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import type { Issue, IssueStatus } from "@/lib/types";

export function IssueDetailView() {
  const id = useIssueId();
  if (id === null) return <NotFoundPanel message="That isn't a valid issue id." />;
  return <IssueDetail id={id} />;
}

function IssueDetail({ id }: { id: number }) {
  const issue = useIssue(id);

  if (issue.isPending) return <DetailSkeleton />;
  if (issue.isError) {
    return isNotFound(issue.error) ? (
      <NotFoundPanel message={`Issue #${id} was not found. It may have been deleted.`} />
    ) : (
      <ErrorBanner error={issue.error} onRetry={() => issue.refetch()} />
    );
  }
  return <IssueDetailContent issue={issue.data} />;
}

const SELECT =
  "mt-1 block w-full rounded-md border border-zinc-300 bg-white px-2 py-1.5 text-sm shadow-sm focus:border-zinc-500 focus:outline-none disabled:opacity-60";

function IssueDetailContent({ issue }: { issue: Issue }) {
  const router = useRouter();
  const users = useUsers();
  const update = useUpdateIssue(issue.id);
  const remove = useDeleteIssue(issue.id);

  // The server says which moves are legal, so only those are offered.
  const statusOptions: IssueStatus[] = [issue.status, ...issue.allowed_transitions];

  return (
    <article className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link href={ROUTES.issues} className="text-sm text-zinc-500 hover:underline">
            ← All issues
          </Link>
          <h1 className="mt-1 text-2xl font-semibold break-words">
            {issue.title} <span className="font-normal text-zinc-400">#{issue.id}</span>
          </h1>
          <div className="mt-2 flex gap-2">
            <StatusBadge status={issue.status} />
            <PriorityBadge priority={issue.priority} />
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href={ROUTES.editIssue(issue.id)}
            className="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm font-medium hover:bg-zinc-50"
          >
            Edit
          </Link>
          <DeleteIssueButton
            deleting={remove.isPending}
            onConfirm={() => remove.mutate(undefined, { onSuccess: () => router.push(ROUTES.issues) })}
          />
        </div>
      </div>

      {update.isError && <ErrorBanner error={update.error} />}
      {remove.isError && <ErrorBanner error={remove.error} />}

      <div className="grid gap-4 md:grid-cols-3">
        <section className="rounded-lg border border-zinc-200 bg-white p-5 md:col-span-2">
          <h2 className="text-sm font-medium text-zinc-500">Description</h2>
          {issue.description ? (
            <p className="mt-2 whitespace-pre-wrap break-words">{issue.description}</p>
          ) : (
            <p className="mt-2 text-zinc-400 italic">No description.</p>
          )}
        </section>

        <aside className="space-y-4 rounded-lg border border-zinc-200 bg-white p-5 text-sm">
          <div>
            <label htmlFor="detail-status" className="font-medium text-zinc-500">
              Status
            </label>
            <select
              id="detail-status"
              className={SELECT}
              value={issue.status}
              disabled={update.isPending}
              onChange={(e) =>
                update.mutate({ status: e.target.value as IssueStatus, version: issue.version })
              }
            >
              {statusOptions.map((status) => (
                <option key={status} value={status}>
                  {STATUS_LABELS[status]}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="detail-assignee" className="font-medium text-zinc-500">
              Assignee
            </label>
            <select
              id="detail-assignee"
              className={SELECT}
              value={issue.assignee_id ?? ""}
              disabled={update.isPending || users.isPending}
              onChange={(e) =>
                update.mutate({
                  assignee_id: e.target.value ? Number(e.target.value) : null,
                  version: issue.version,
                })
              }
            >
              <option value="">Unassigned</option>
              {users.data?.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.name}
                </option>
              ))}
            </select>
          </div>
          <dl className="space-y-2 border-t border-zinc-100 pt-4 text-zinc-600">
            <div className="flex justify-between gap-2">
              <dt>Created</dt>
              <dd>
                <time dateTime={issue.created_at}>{formatDateTime(issue.created_at)}</time>
              </dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt>Updated</dt>
              <dd>
                <time dateTime={issue.updated_at}>{formatDateTime(issue.updated_at)}</time>
              </dd>
            </div>
          </dl>
        </aside>
      </div>
    </article>
  );
}

export function DetailSkeleton() {
  return (
    <div aria-busy="true" aria-label="Loading" className="space-y-3">
      <div className="h-8 w-2/3 animate-pulse rounded bg-zinc-200/70" />
      <div className="h-40 animate-pulse rounded-lg bg-zinc-200/70" />
    </div>
  );
}
