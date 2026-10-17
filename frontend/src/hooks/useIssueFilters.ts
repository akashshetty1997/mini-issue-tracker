"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

import {
  DEFAULT_FILTERS,
  parseFilters,
  toSearchParams,
  type IssueFilterState,
} from "@/lib/issueFilters";

/** Issue list filters backed by the URL query string. */
export function useIssueFilters() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const filters = useMemo(() => parseFilters(searchParams), [searchParams]);

  const navigate = useCallback(
    (next: IssueFilterState) => {
      const query = toSearchParams(next).toString();
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    },
    [pathname, router],
  );

  /** Apply a change. Any change other than the page itself goes back to page 1. */
  const setFilters = useCallback(
    (patch: Partial<IssueFilterState>) => navigate({ ...filters, page: 1, ...patch }),
    [filters, navigate],
  );

  const resetFilters = useCallback(
    () => navigate({ ...DEFAULT_FILTERS, sort: filters.sort }),
    [filters.sort, navigate],
  );

  return { filters, setFilters, resetFilters };
}
