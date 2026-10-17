import {
  PRIORITY_BADGE_CLASSES,
  PRIORITY_LABELS,
  STATUS_BADGE_CLASSES,
  STATUS_LABELS,
} from "@/lib/constants";
import type { IssuePriority, IssueStatus } from "@/lib/types";

const BASE = "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset";

export function StatusBadge({ status }: { status: IssueStatus }) {
  return <span className={`${BASE} ${STATUS_BADGE_CLASSES[status]}`}>{STATUS_LABELS[status]}</span>;
}

export function PriorityBadge({ priority }: { priority: IssuePriority }) {
  return (
    <span className={`${BASE} ${PRIORITY_BADGE_CLASSES[priority]}`}>
      {PRIORITY_LABELS[priority]}
    </span>
  );
}
