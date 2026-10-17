import Link from "next/link";

import { PriorityBadge, StatusBadge } from "@/components/issues/Badges";
import { ROUTES } from "@/lib/constants";
import { formatDateTime, formatRelative } from "@/lib/format";
import type { Issue } from "@/lib/types";

export function IssueTable({ issues }: { issues: Issue[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-200 bg-white">
      <table className="min-w-full divide-y divide-zinc-200 text-sm">
        <thead className="bg-zinc-50 text-left text-xs font-medium uppercase tracking-wide text-zinc-500">
          <tr>
            <th scope="col" className="px-4 py-3">
              Title
            </th>
            <th scope="col" className="px-4 py-3">
              Status
            </th>
            <th scope="col" className="px-4 py-3">
              Priority
            </th>
            <th scope="col" className="hidden px-4 py-3 md:table-cell">
              Assignee
            </th>
            <th scope="col" className="hidden px-4 py-3 sm:table-cell">
              Updated
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100">
          {issues.map((issue) => (
            <tr key={issue.id} className="hover:bg-zinc-50">
              <td className="max-w-md px-4 py-3">
                <Link
                  href={ROUTES.issue(issue.id)}
                  className="font-medium text-zinc-900 hover:underline"
                >
                  {issue.title}
                </Link>
                <span className="ml-2 text-xs text-zinc-400">#{issue.id}</span>
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={issue.status} />
              </td>
              <td className="px-4 py-3">
                <PriorityBadge priority={issue.priority} />
              </td>
              <td className="hidden px-4 py-3 text-zinc-700 md:table-cell">
                {issue.assignee?.name ?? <span className="text-zinc-400">Unassigned</span>}
              </td>
              <td className="hidden whitespace-nowrap px-4 py-3 text-zinc-500 sm:table-cell">
                <time dateTime={issue.updated_at} title={formatDateTime(issue.updated_at)}>
                  {formatRelative(issue.updated_at)}
                </time>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
