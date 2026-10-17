import { Suspense } from "react";

import { DetailSkeleton } from "@/views/IssueDetailView";
import { EditIssueView } from "@/views/IssueFormViews";

export default function EditIssuePage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Edit issue</h1>
      <div className="rounded-lg border border-zinc-200 bg-white p-6">
        <Suspense fallback={<DetailSkeleton />}>
          <EditIssueView />
        </Suspense>
      </div>
    </div>
  );
}
