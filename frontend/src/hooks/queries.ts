"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { issuesApi } from "@/lib/api/issues";
import { referenceApi } from "@/lib/api/reference";
import type { Issue, IssueCreate, IssueListQuery, IssueUpdate } from "@/lib/types";

export const queryKeys = {
  issues: ["issues"] as const,
  issueList: (query: IssueListQuery) => ["issues", "list", query] as const,
  issue: (id: number) => ["issues", "detail", id] as const,
  users: ["users"] as const,
  meta: ["meta"] as const,
};

export function useIssueList(query: IssueListQuery) {
  return useQuery({
    queryKey: queryKeys.issueList(query),
    queryFn: ({ signal }) => issuesApi.list(query, signal),
    // Keep showing the current page while the next filter/page loads.
    placeholderData: keepPreviousData,
  });
}

export function useIssue(id: number) {
  return useQuery({
    queryKey: queryKeys.issue(id),
    queryFn: ({ signal }) => issuesApi.get(id, signal),
  });
}

export function useUsers() {
  return useQuery({
    queryKey: queryKeys.users,
    queryFn: ({ signal }) => referenceApi.users(signal),
    staleTime: Infinity,
  });
}

export function useMeta() {
  return useQuery({
    queryKey: queryKeys.meta,
    queryFn: ({ signal }) => referenceApi.meta(signal),
    staleTime: Infinity,
  });
}

function useCacheIssue() {
  const queryClient = useQueryClient();
  return (issue: Issue) => {
    queryClient.setQueryData(queryKeys.issue(issue.id), issue);
    return queryClient.invalidateQueries({ queryKey: [...queryKeys.issues, "list"] });
  };
}

export function useCreateIssue() {
  const cacheIssue = useCacheIssue();
  return useMutation({
    mutationFn: (data: IssueCreate) => issuesApi.create(data),
    onSuccess: cacheIssue,
  });
}

export function useUpdateIssue(id: number) {
  const queryClient = useQueryClient();
  const cacheIssue = useCacheIssue();
  return useMutation({
    mutationFn: (data: IssueUpdate) => issuesApi.update(id, data),
    onSuccess: cacheIssue,
    // A rejected update (e.g. 409 because another user changed the issue) usually means
    // our copy is stale; refetch so the page shows the real state and legal options.
    onError: () => queryClient.invalidateQueries({ queryKey: queryKeys.issue(id) }),
  });
}

export function useDeleteIssue(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => issuesApi.remove(id),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: queryKeys.issue(id) });
      return queryClient.invalidateQueries({ queryKey: [...queryKeys.issues, "list"] });
    },
  });
}
