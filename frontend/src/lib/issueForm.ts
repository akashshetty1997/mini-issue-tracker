/** Pure logic behind the issue create/edit form. */
import type { Issue, IssuePriority, IssueStatus, IssueUpdate, Meta } from "@/lib/types";

export interface IssueFormValues {
  title: string;
  description: string;
  status: IssueStatus;
  priority: IssuePriority;
  assigneeId: number | null;
}

export type FieldErrors = Partial<Record<keyof IssueFormValues, string>>;

/** Mirrors the server's rules so most mistakes are caught before a round trip. */
export function validateIssueForm(values: IssueFormValues, limits: Meta["limits"]): FieldErrors {
  const errors: FieldErrors = {};
  const title = values.title.trim();
  if (title.length < limits.title_min_length) errors.title = "Title is required.";
  else if (title.length > limits.title_max_length)
    errors.title = `Title must be at most ${limits.title_max_length} characters.`;
  if (values.description.length > limits.description_max_length)
    errors.description = `Description must be at most ${limits.description_max_length} characters.`;
  return errors;
}

export function toFormValues(issue: Issue): IssueFormValues {
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
