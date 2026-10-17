"use client";

import { useRouter } from "next/navigation";

import { IssueForm, type IssueFormValues } from "@/components/issues/IssueForm";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { NotFoundPanel } from "@/components/ui/NotFoundPanel";
import { useCreateIssue, useIssue, useMeta, useUpdateIssue, useUsers } from "@/hooks/queries";
import { useIssueId } from "@/hooks/useIssueId";
import { ROUTES, STATUSES } from "@/lib/constants";
import { isNotFound } from "@/lib/errors";
import type { Issue, IssueUpdate } from "@/lib/types";
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

/** PATCH semantics: send only what changed. */
export function changedFields(before: IssueFormValues, after: IssueFormValues): IssueUpdate {
  const changes: IssueUpdate = {};
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
  const router = useRouter();
  const issue = useIssue(id);
  const update = useUpdateIssue(id);
  const deps = useFormDependencies();

  if (issue.isError) {
    return isNotFound(issue.error) ? (
      <NotFoundPanel message={`Issue #${id} was not found. It may have been deleted.`} />
    ) : (
      <ErrorBanner error={issue.error} onRetry={() => issue.refetch()} />
    );
  }
  if (deps.error) return <ErrorBanner error={deps.error} />;
  if (issue.isPending || deps.pending || !deps.meta.data) return <DetailSkeleton />;

  const initialValues = toFormValues(issue.data);
  const backToIssue = () => router.push(ROUTES.issue(id));

  return (
    <IssueForm
      initialValues={initialValues}
      statusOptions={[issue.data.status, ...issue.data.allowed_transitions]}
      users={deps.users.data ?? []}
      limits={deps.meta.data.limits}
      submitLabel="Save changes"
      submitting={update.isPending}
      submitError={update.error}
      onCancel={backToIssue}
      onSubmit={(values) => {
        const changes = changedFields(initialValues, values);
        if (Object.keys(changes).length === 0) return backToIssue();
        update.mutate(changes, { onSuccess: backToIssue });
      }}
    />
  );
}
