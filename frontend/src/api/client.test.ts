import { beforeEach, describe, expect, it, vi } from "vitest";

import * as auth from "../auth/authClient";
import { ApiError, apiRequest } from "./client";

vi.mock("../auth/authClient", async () => {
  const actual = await vi.importActual<typeof import("../auth/authClient")>("../auth/authClient");
  return { ...actual, idToken: vi.fn() };
});

describe("authenticated API client", () => {
  beforeEach(() => {
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
});
