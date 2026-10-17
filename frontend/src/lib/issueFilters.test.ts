import { describe, expect, it } from "vitest";

import {
  DEFAULT_FILTERS,
  hasActiveFilters,
  parseFilters,
  toListQuery,
  toSearchParams,
  type IssueFilterState,
} from "./issueFilters";

const parse = (query: string) => parseFilters(new URLSearchParams(query));

describe("parseFilters", () => {
  it("returns defaults for an empty query", () => {
    expect(parse("")).toEqual(DEFAULT_FILTERS);
  });

  it("reads every filter", () => {
    expect(parse("status=open&status=in_progress&priority=high&assignee=3&q=login&sort=title&page=2")).toEqual({
      status: ["open", "in_progress"],
      priority: ["high"],
      assigneeId: 3,
      q: "login",
      sort: "title",
      page: 2,
    });
  });

  it("drops malformed and unknown values instead of failing", () => {
    expect(parse("status=bogus&status=open&status=open&priority=p0&assignee=abc&sort=evil&page=-3")).toEqual({
      ...DEFAULT_FILTERS,
      status: ["open"],
    });
    expect(parse("assignee=0&page=1.5").assigneeId).toBeNull();
  });
});

describe("toSearchParams", () => {
  it("omits defaults so URLs stay short", () => {
    expect(toSearchParams(DEFAULT_FILTERS).toString()).toBe("");
  });

  it("round-trips through parseFilters", () => {
    const filters: IssueFilterState = {
      status: ["resolved", "closed"],
      priority: ["low"],
      assigneeId: 7,
      q: "slow export",
      sort: "-priority",
      page: 3,
    };

    expect(parseFilters(toSearchParams(filters))).toEqual(filters);
  });

  it("trims the search term", () => {
    expect(toSearchParams({ ...DEFAULT_FILTERS, q: "  login  " }).get("q")).toBe("login");
    expect(toSearchParams({ ...DEFAULT_FILTERS, q: "   " }).has("q")).toBe(false);
  });
});

describe("toListQuery", () => {
  it("maps UI state to API parameters, including the page offset", () => {
    const query = toListQuery({ ...DEFAULT_FILTERS, status: ["open"], assigneeId: 2, page: 3 }, 20);

    expect(query).toEqual({
      status: ["open"],
      priority: undefined,
      assignee_id: 2,
      q: undefined,
      sort: "-created_at",
      limit: 20,
      offset: 40,
    });
  });
});

describe("hasActiveFilters", () => {
  it("ignores sort and page", () => {
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, sort: "title", page: 4 })).toBe(false);
    expect(hasActiveFilters({ ...DEFAULT_FILTERS, priority: ["critical"] })).toBe(true);
  });
});
