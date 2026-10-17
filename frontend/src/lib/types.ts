/**
 * Domain types, derived from the backend's OpenAPI schema (see `npm run gen:api`).
 * Never hand-write these: regenerate when the API changes.
 */
import type { components, operations } from "@/lib/api/schema";

type Schemas = components["schemas"];

export type Issue = Schemas["IssueRead"];
export type IssueCreate = Schemas["IssueCreate"];
export type IssueUpdate = Schemas["IssueUpdate"];
export type IssuePage = Schemas["Page_IssueRead_"];
export type IssueStatus = Schemas["IssueStatus"];
export type IssuePriority = Schemas["IssuePriority"];
export type User = Schemas["UserRead"];
export type Meta = Schemas["MetaRead"];
export type ErrorEnvelope = Schemas["ErrorResponse"];

export type IssueListQuery = NonNullable<
  operations["list_issues_api_v1_issues_get"]["parameters"]["query"]
>;
