import { describe, expect, it } from "vitest";

import { ApiError } from "./api/client";
import { describeError } from "./errors";

describe("describeError", () => {
  it("explains rate limits with the retry delay", () => {
    const error = new ApiError(429, "RATE_LIMITED", "Too many requests.", null, null, 12);

    expect(describeError(error)).toBe("Too many requests. Please retry in 12s.");
  });

  it("explains edit conflicts", () => {
    const error = new ApiError(409, "VERSION_CONFLICT", "changed");

    expect(describeError(error)).toMatch(/Someone else changed this issue/);
  });

  it("never leaks unknown errors", () => {
    expect(describeError(new TypeError("x is undefined"))).toBe(
      "Something went wrong. Please try again.",
    );
  });
});
