import type { Metadata } from "next";
import Link from "next/link";

import { ROUTES } from "@/lib/constants";

import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mini Issue Tracker",
  description: "Create, triage and track software issues.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-zinc-50 text-zinc-900">
        <header className="border-b border-zinc-200 bg-white">
          <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
            <Link href={ROUTES.issues} className="text-lg font-semibold tracking-tight">
              Mini Issue Tracker
            </Link>
            <Link
              href={ROUTES.newIssue}
              className="rounded-md bg-zinc-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-zinc-700"
            >
              New issue
            </Link>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-4 py-6">
          <Providers>{children}</Providers>
        </main>
      </body>
    </html>
  );
}
