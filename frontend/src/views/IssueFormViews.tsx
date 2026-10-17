"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { IssueForm, type IssueFormValues } from "@/components/issues/IssueForm";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { NotFoundPanel } from "@/components/ui/NotFoundPanel";
import { useCreateIssue, useIssue, useMeta, useUpdateIssue, useUsers } from "@/hooks/queries";
import { useIssueId } from "@/hooks/useIssueId";
import { ROUTES, STATUSES } from "@/lib/constants";
import { isNotFound, isVersionConflict } from "@/lib/errors";
import type { Issue, IssueUpdate, Meta, User } from "@/lib/types";
import { DetailSkeleton } from "@/views/IssueDetailView";

const NEW_ISSUE: IssueFormValues = {
  title: "",
  description: "",
  status: "open",
  priority: "medium",
  assigneeId: null,
};

function toFormValues(issue: Issue): IssueFormValues {
  return {
    title: issue.title,
    description: issue.description,
    status: issue.status,
    priority: issue.priority,
    assigneeId: issue.assignee_id,
  };
}

type IssueChanges = Omit<IssueUpdate, "version">;

/** PATCH semantics: send only what changed. */
export function changedFields(before: IssueFormValues, after: IssueFormValues): IssueChanges {
  const changes: IssueChanges = {};
  if (after.title !== before.title) changes.title = after.title;
  if (after.description !== before.description) changes.description = after.description;
  if (after.status !== before.status) changes.status = after.status;
  if (after.priority !== before.priority) changes.priority = after.priority;
  if (after.assigneeId !== before.assigneeId) changes.assignee_id = after.assigneeId;
  return changes;
}

function useFormDependencies() {
  const meta = useMeta();
  const users = useUsers();
  return {
    meta,
    users,
    pending: meta.isPending || users.isPending,
    error: meta.error ?? users.error,
  };
}

export function NewIssueView() {
  const router = useRouter();
  const create = useCreateIssue();
  const deps = useFormDependencies();

  if (deps.error) return <ErrorBanner error={deps.error} />;
  if (deps.pending || !deps.meta.data) return <DetailSkeleton />;

  return (
    <IssueForm
      initialValues={NEW_ISSUE}
      statusOptions={STATUSES}
      users={deps.users.data ?? []}
      limits={deps.meta.data.limits}
      submitLabel="Create issue"
      submitting={create.isPending}
      submitError={create.error}
      onCancel={() => router.push(ROUTES.issues)}
      onSubmit={(values) =>
        create.mutate(
          {
            title: values.title,
            description: values.description,
            status: values.status,
            priority: values.priority,
            assignee_id: values.assigneeId,
          },
          { onSuccess: (issue) => router.push(ROUTES.issue(issue.id)) },
        )
      }
    />
  );
}

export function EditIssueView() {
  const id = useIssueId();
  if (id === null) return <NotFoundPanel message="That isn't a valid issue id." />;
  return <EditIssue id={id} />;
}

function EditIssue({ id }: { id: number }) {
  const issue = useIssue(id);
  const deps = useFormDependencies();
  // The issue as it was when the form loaded. Edits are diffed against it and saved
  // with its version, even if a newer copy arrives in the background.
  const [base, setBase] = useState<Issue | null>(null);
  if (base === null && issue.data) setBase(issue.data);

  if (issue.isError && base === null) {
    return isNotFound(issue.error) ? (
      <NotFoundPanel message={`Issue #${id} was not found. It may have been deleted.`} />
    ) : (
      <ErrorBanner error={issue.error} onRetry={() => issue.refetch()} />
    );
  }
  if (deps.error) return <ErrorBanner error={deps.error} />;
  if (base === null || deps.pending || !deps.meta.data) return <DetailSkeleton />;

  return (
    <EditIssueForm
      // Remount (fresh form state and mutation) when the user loads a newer version.
      key={base.version}
      base={base}
      latest={issue.data ?? base}
      onLoadLatest={() => issue.data && setBase(issue.data)}
      users={deps.users.data ?? []}
      limits={deps.meta.data.limits}
    />
  );
}

interface EditIssueFormProps {
  base: Issue;
  latest: Issue;
  onLoadLatest: () => void;
  users: User[];
  limits: Meta["limits"];
}

function EditIssueForm({ base, latest, onLoadLatest, users, limits }: EditIssueFormProps) {
  const router = useRouter();
  const update = useUpdateIssue(base.id);
  const conflict = isVersionConflict(update.error);
  const initialValues = toFormValues(base);
  const backToIssue = () => router.push(ROUTES.issue(base.id));

  return (
    <div className="space-y-5">
      {conflict && (
        <div
          role="alert"
          className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900"
        >
          <p>Someone else saved changes to this issue after you opened it.</p>
          <button
            type="button"
            onClick={onLoadLatest}
            disabled={latest.version === base.version}
            className="rounded-md bg-amber-700 px-3 py-1.5 font-medium text-white hover:bg-amber-800 disabled:opacity-60"
          >
            Discard my edits and load the latest version
          </button>
        </div>
      )}
      <IssueForm
        initialValues={initialValues}
        statusOptions={[base.status, ...base.allowed_transitions]}
        users={users}
        limits={limits}
        submitLabel="Save changes"
        submitting={update.isPending}
        submitError={conflict ? null : update.error}
        onCancel={backToIssue}
        onSubmit={(values) => {
          const changes = changedFields(initialValues, values);
          if (Object.keys(changes).length === 0) return backToIssue();
          update.mutate({ ...changes, version: base.version }, { onSuccess: backToIssue });
        }}
      />
    </div>
  );
}
