import { http } from "@/lib/api/client";
import { API_V1_PREFIX } from "@/lib/constants";
import type { Issue, IssueCreate, IssueListQuery, IssuePage, IssueUpdate } from "@/lib/types";

const ISSUES_PATH = `${API_V1_PREFIX}/issues`;

export const issuesApi = {
  list: (query: IssueListQuery, signal?: AbortSignal) =>
    http.get<IssuePage>(ISSUES_PATH, query, signal),
  get: (id: number, signal?: AbortSignal) =>
    http.get<Issue>(`${ISSUES_PATH}/${id}`, undefined, signal),
  create: (data: IssueCreate) => http.post<Issue>(ISSUES_PATH, data),
  update: (id: number, data: IssueUpdate) => http.patch<Issue>(`${ISSUES_PATH}/${id}`, data),
  remove: (id: number) => http.delete(`${ISSUES_PATH}/${id}`),
};
