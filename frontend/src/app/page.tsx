import { Suspense } from "react";

import { IssueListView, ListSkeleton } from "@/views/IssueListView";

export default function IssuesPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Issues</h1>
      {/* The list reads filters from the URL (useSearchParams), which needs a Suspense
          boundary so the rest of the page can still be prerendered. */}
      <Suspense fallback={<ListSkeleton />}>
        <IssueListView />
      </Suspense>
    </div>
  );
}
