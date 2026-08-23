import { beforeEach, describe, expect, it, vi } from "vitest";

import * as auth from "../auth/authClient";
import { ApiError, apiRequest, executeTemporaryQuery } from "./client";

vi.mock("../auth/authClient", async () => {
  const actual = await vi.importActual<typeof import("../auth/authClient")>("../auth/authClient");
  return { ...actual, idToken: vi.fn() };
});

describe("authenticated API client", () => {
  beforeEach(() => {
    vi.useRealTimers();
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.test/");
    vi.mocked(auth.idToken).mockResolvedValue("fresh-id-token");
    vi.stubGlobal("fetch", vi.fn());
  });

  it("attaches a fresh bearer token and disables caching", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await expect(apiRequest<{ status: string }>("/health")).resolves.toEqual({ status: "ok" });
    expect(auth.idToken).toHaveBeenCalledOnce();
    const call = vi.mocked(fetch).mock.calls[0];
    expect(call).toBeDefined();
    const [url, init] = call!;
    expect(url).toBe("https://api.example.test/health");
    expect(init?.cache).toBe("no-store");
    const headers = new Headers(init?.headers);
    expect(headers.get("Authorization")).toBe("Bearer fresh-id-token");
  });

  it("preserves stable backend error evidence without leaking bodies", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: "FORBIDDEN",
            message: "You cannot modify this media",
            request_id: "request-123",
            details: {},
          },
        }),
        { status: 403, headers: { "Content-Type": "application/json" } },
      ),
    );
    const error = await apiRequest("/media/tags", { method: "POST", body: "{}" }).catch(
      (caught) => caught,
    );
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      code: "FORBIDDEN",
      status: 403,
      requestId: "request-123",
      message: "You cannot modify this media",
    });
  });

  it("does not call the API after local session expiry", async () => {
    vi.mocked(auth.idToken).mockRejectedValue(new Error("Your session has expired."));
    await expect(apiRequest("/health")).rejects.toThrow(/session has expired/i);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("polls an asynchronous temporary query until fresh results are ready", async () => {
    vi.useFakeTimers();
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            query_id: "query-1",
            processing_status: "AWAITING_UPLOAD",
            retry_after_seconds: 3,
          }),
          { status: 202, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            query_id: "query-1",
            processing_status: "PROCESSING",
            retry_after_seconds: 3,
          }),
          { status: 202, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            query_id: "query-1",
            processing_status: "READY",
            detected_species_counts: { dingo: 1 },
            model_version: "supplied-v1",
            media: [],
            total: 0,
            truncated: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );

    const result = executeTemporaryQuery({
      query_id: "query-1",
      temp_key: "query-temp/actor/query-1/query.jpg",
      upload_url: "https://storage.example/put",
      required_headers: {},
      expires_in: 300,
    });
    await vi.advanceTimersByTimeAsync(6000);
    await expect(result).resolves.toMatchObject({
      processing_status: "READY",
      detected_species_counts: { dingo: 1 },
    });
    expect(vi.mocked(fetch)).toHaveBeenCalledTimes(3);
    expect(vi.mocked(fetch).mock.calls.map((call) => call[1]?.method)).toEqual([
      "POST",
      "GET",
      "GET",
    ]);
  });
});
