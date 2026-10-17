import { afterEach, describe, expect, it, vi } from "vitest";

import { API_BASE_URL } from "@/lib/config";

import { ApiError, buildUrl, http, toApiError } from "./client";

function jsonResponse(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

describe("buildUrl", () => {
  it("repeats array values and skips empty ones", () => {
    const url = buildUrl("/api/v1/issues", {
      status: ["open", "closed"],
      q: "",
      assignee_id: undefined,
      limit: 20,
    });

    expect(url).toBe(`${API_BASE_URL}/api/v1/issues?status=open&status=closed&limit=20`);
  });

  it("encodes special characters", () => {
    expect(buildUrl("/x", { q: "100% & more" })).toBe(`${API_BASE_URL}/x?q=100%25+%26+more`);
  });
});

describe("toApiError", () => {
  it("reads the error envelope", () => {
    const response = new Response(null, { status: 422 });
    const error = toApiError(response, {
      error: {
        code: "VALIDATION_ERROR",
        message: "The request is invalid.",
        details: [
          { location: "body", field: "title", message: "String should have at least 1 character" },
          { location: "body", field: "title", message: "second message is ignored" },
          { location: "body", field: null, message: "model-level error" },
        ],
        request_id: "req-1",
      },
    });

    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("VALIDATION_ERROR");
    expect(error.requestId).toBe("req-1");
    expect(error.fieldErrors()).toEqual({ title: "String should have at least 1 character" });
  });

  it("parses Retry-After on 429", () => {
    const response = new Response(null, { status: 429, headers: { "Retry-After": "42" } });
    const error = toApiError(response, {
      error: { code: "RATE_LIMITED", message: "Too many requests.", details: null, request_id: null },
    });

    expect(error.retryAfterSeconds).toBe(42);
  });

  it("falls back gracefully when the body is not an envelope", () => {
    const response = new Response(null, { status: 502, headers: { "X-Request-ID": "gw-7" } });
    const error = toApiError(response, "<html>Bad gateway</html>");

    expect(error.code).toBe("UNKNOWN_ERROR");
    expect(error.message).toBe("Request failed with status 502.");
    expect(error.requestId).toBe("gw-7");
    expect(error.fieldErrors()).toEqual({});
  });
});

describe("http", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("returns parsed JSON on success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, { id: 1 })));

    await expect(http.get("/api/v1/issues/1")).resolves.toEqual({ id: 1 });
  });

  it("sends JSON bodies", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(201, { id: 2 }));
    vi.stubGlobal("fetch", fetchMock);

    await http.post("/api/v1/issues", { title: "x" });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
    expect(init.body).toBe('{"title":"x"}');
  });

  it("resolves 204 responses without parsing a body", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));

    await expect(http.delete("/api/v1/issues/1")).resolves.toBeUndefined();
  });

  it("throws ApiError for error responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(404, {
          error: {
            code: "ISSUE_NOT_FOUND",
            message: "Issue 9 was not found.",
            details: null,
            request_id: "r",
          },
        }),
      ),
    );

    await expect(http.get("/api/v1/issues/9")).rejects.toMatchObject({
      status: 404,
      code: "ISSUE_NOT_FOUND",
    });
  });

  it("turns network failures into a friendly ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));

    await expect(http.get("/api/v1/issues")).rejects.toMatchObject({
      status: 0,
      code: "NETWORK_ERROR",
    });
  });
});
