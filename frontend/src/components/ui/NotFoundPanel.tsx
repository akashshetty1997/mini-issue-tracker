import Link from "next/link";

import { ROUTES } from "@/lib/constants";

export function NotFoundPanel({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-10 text-center">
      <p className="font-medium">{message}</p>
      <Link
        href={ROUTES.issues}
        className="mt-2 inline-block text-sm text-zinc-600 underline underline-offset-2"
      >
        Back to all issues
      </Link>
    </div>
  );
}
