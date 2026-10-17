import { NewIssueView } from "@/views/IssueFormViews";

export default function NewIssuePage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">New issue</h1>
      <div className="rounded-lg border border-zinc-200 bg-white p-6">
        <NewIssueView />
      </div>
    </div>
  );
}
