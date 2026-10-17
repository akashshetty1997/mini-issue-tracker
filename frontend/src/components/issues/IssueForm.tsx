"use client";

import { useState, type FormEvent } from "react";

import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { ApiError } from "@/lib/api/client";
import { PRIORITIES, PRIORITY_LABELS, STATUS_LABELS } from "@/lib/constants";
import type { IssuePriority, IssueStatus, Meta, User } from "@/lib/types";

export interface IssueFormValues {
  title: string;
  description: string;
  status: IssueStatus;
  priority: IssuePriority;
  assigneeId: number | null;
}

type FieldErrors = Partial<Record<keyof IssueFormValues, string>>;

interface IssueFormProps {
  initialValues: IssueFormValues;
  statusOptions: IssueStatus[];
  users: User[];
  limits: Meta["limits"];
  submitLabel: string;
  submitting: boolean;
  submitError: unknown;
  onSubmit: (values: IssueFormValues) => void;
  onCancel: () => void;
}

// Server field names (snake_case) -> form field names.
const SERVER_FIELDS: Record<string, keyof IssueFormValues> = {
  title: "title",
  description: "description",
  status: "status",
  priority: "priority",
  assignee_id: "assigneeId",
};

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

function serverFieldErrors(error: unknown): FieldErrors {
  if (!(error instanceof ApiError)) return {};
  const errors: FieldErrors = {};
  for (const [field, message] of Object.entries(error.fieldErrors())) {
    const formField = SERVER_FIELDS[field];
    if (formField) errors[formField] = message;
  }
  return errors;
}

const INPUT =
  "mt-1 block w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500 aria-[invalid=true]:border-red-500";

function Field({
  id,
  label,
  error,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-zinc-700">
        {label}
      </label>
      {children}
      {error && (
        <p id={`${id}-error`} className="mt-1 text-sm text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}

export function IssueForm({
  initialValues,
  statusOptions,
  users,
  limits,
  submitLabel,
  submitting,
  submitError,
  onSubmit,
  onCancel,
}: IssueFormProps) {
  const [values, setValues] = useState(initialValues);
  const [clientErrors, setClientErrors] = useState<FieldErrors>({});

  const errors = { ...serverFieldErrors(submitError), ...clientErrors };
  const hasFieldErrors = Object.keys(serverFieldErrors(submitError)).length > 0;

  function update<K extends keyof IssueFormValues>(field: K, value: IssueFormValues[K]) {
    setValues((current) => ({ ...current, [field]: value }));
    setClientErrors((current) => ({ ...current, [field]: undefined }));
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const validationErrors = validateIssueForm(values, limits);
    setClientErrors(validationErrors);
    if (Object.keys(validationErrors).length === 0) {
      onSubmit({ ...values, title: values.title.trim() });
    }
  }

  const describedBy = (field: keyof IssueFormValues) =>
    errors[field] ? `${field}-error` : undefined;

  return (
    <form noValidate onSubmit={handleSubmit} className="space-y-5">
      {submitError != null && !hasFieldErrors && <ErrorBanner error={submitError} />}

      <Field id="title" label="Title" error={errors.title}>
        <input
          id="title"
          className={INPUT}
          value={values.title}
          maxLength={limits.title_max_length}
          aria-invalid={Boolean(errors.title)}
          aria-describedby={describedBy("title")}
          onChange={(e) => update("title", e.target.value)}
          autoFocus
        />
      </Field>

      <Field id="description" label="Description" error={errors.description}>
        <textarea
          id="description"
          rows={6}
          className={INPUT}
          value={values.description}
          maxLength={limits.description_max_length}
          aria-invalid={Boolean(errors.description)}
          aria-describedby={describedBy("description")}
          onChange={(e) => update("description", e.target.value)}
        />
      </Field>

      <div className="grid gap-5 sm:grid-cols-3">
        <Field id="status" label="Status" error={errors.status}>
          <select
            id="status"
            className={INPUT}
            value={values.status}
            onChange={(e) => update("status", e.target.value as IssueStatus)}
          >
            {statusOptions.map((status) => (
              <option key={status} value={status}>
                {STATUS_LABELS[status]}
              </option>
            ))}
          </select>
        </Field>

        <Field id="priority" label="Priority" error={errors.priority}>
          <select
            id="priority"
            className={INPUT}
            value={values.priority}
            onChange={(e) => update("priority", e.target.value as IssuePriority)}
          >
            {PRIORITIES.map((priority) => (
              <option key={priority} value={priority}>
                {PRIORITY_LABELS[priority]}
              </option>
            ))}
          </select>
        </Field>

        <Field id="assignee" label="Assignee" error={errors.assigneeId}>
          <select
            id="assignee"
            className={INPUT}
            value={values.assigneeId ?? ""}
            aria-invalid={Boolean(errors.assigneeId)}
            onChange={(e) => update("assigneeId", e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Unassigned</option>
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.name}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <div className="flex justify-end gap-3">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-zinc-300 bg-white px-4 py-2 text-sm font-medium hover:bg-zinc-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-60"
        >
          {submitting ? "Saving…" : submitLabel}
        </button>
      </div>
    </form>
  );
}
