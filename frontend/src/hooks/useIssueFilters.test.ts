import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useIssueFilters } from "./useIssueFilters";

const replace = vi.fn();
let currentQuery = "";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(currentQuery),
}));

describe("useIssueFilters", () => {
  beforeEach(() => {
    replace.mockClear();
    currentQuery = "";
  });

  it("exposes the filters parsed from the URL", () => {
    currentQuery = "status=open&q=login&page=2";

    const { result } = renderHook(() => useIssueFilters());

    expect(result.current.filters).toMatchObject({ status: ["open"], q: "login", page: 2 });
  });

  it("writes changes to the URL and resets to page 1", () => {
    currentQuery = "status=open&page=3";
    const { result } = renderHook(() => useIssueFilters());

    act(() => result.current.setFilters({ priority: ["high"] }));

    expect(replace).toHaveBeenCalledWith("/?status=open&priority=high", { scroll: false });
  });

  it("keeps the requested page when paginating", () => {
    const { result } = renderHook(() => useIssueFilters());

    act(() => result.current.setFilters({ page: 2 }));

    expect(replace).toHaveBeenCalledWith("/?page=2", { scroll: false });
  });

  it("resets filters but keeps the chosen sort order", () => {
    currentQuery = "status=open&q=x&sort=title&page=2";
    const { result } = renderHook(() => useIssueFilters());

    act(() => result.current.resetFilters());

    expect(replace).toHaveBeenCalledWith("/?sort=title", { scroll: false });
  });
});
