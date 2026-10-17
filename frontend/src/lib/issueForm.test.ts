import { describe, expect, it } from "vitest";

import { changedFields, validateIssueForm, type IssueFormValues } from "./issueForm";

const LIMITS = {
  title_min_length: 1,
  title_max_length: 10,
  description_max_length: 20,
  default_page_size: 20,
  max_page_size: 100,
  search_max_length: 200,
};

const VALUES: IssueFormValues = {
  title: "Bug",
  description: "",
  status: "open",
  priority: "medium",
  assigneeId: null,
};

describe("validateIssueForm", () => {
  it("accepts valid values", () => {
    expect(validateIssueForm(VALUES, LIMITS)).toEqual({});
  });

  it("rejects blank and too-long titles using the server's limits", () => {
    expect(validateIssueForm({ ...VALUES, title: "   " }, LIMITS).title).toBe("Title is required.");
    expect(validateIssueForm({ ...VALUES, title: "x".repeat(11) }, LIMITS).title).toMatch(/at most 10/);
  });

  it("rejects descriptions over the limit", () => {
    expect(validateIssueForm({ ...VALUES, description: "x".repeat(21) }, LIMITS).description).toMatch(
      /at most 20/,
    );
  });
});

describe("changedFields", () => {
  it("returns only what changed, using API field names", () => {
    expect(changedFields(VALUES, { ...VALUES, title: "Bug!", assigneeId: 4 })).toEqual({
      title: "Bug!",
      assignee_id: 4,
    });
  });

  it("can express unassigning", () => {
    expect(changedFields({ ...VALUES, assigneeId: 4 }, VALUES)).toEqual({ assignee_id: null });
  });

  it("is empty when nothing changed", () => {
    expect(changedFields(VALUES, { ...VALUES })).toEqual({});
  });
});
