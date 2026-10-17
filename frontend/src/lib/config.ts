/**
 * Environment-driven configuration.
 *
 * NEXT_PUBLIC_* values are inlined into the browser bundle at build time, so changing
 * them requires a rebuild (see README, "Known limitations").
 */
export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/+$/,
  "",
);
