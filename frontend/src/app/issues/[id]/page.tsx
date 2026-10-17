import { Suspense } from "react";

import { DetailSkeleton, IssueDetailView } from "@/views/IssueDetailView";

export default function IssuePage() {
  // The view reads the id with useParams, which suspends for dynamic routes.
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <IssueDetailView />
    </Suspense>
  );
}
