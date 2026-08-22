import { describe, expect, it } from "vitest";

import { readPublicConfig } from "./config";

const valid = {
  VITE_AWS_REGION: "ap-southeast-2",
  VITE_API_BASE_URL: "https://api.example",
  VITE_COGNITO_USER_POOL_ID: "pool",
  VITE_COGNITO_CLIENT_ID: "client",
  VITE_COGNITO_DOMAIN: "https://auth.example",
  VITE_OAUTH_REDIRECT_URI: "http://localhost:5173/auth/callback",
  VITE_OAUTH_LOGOUT_URI: "http://localhost:5173/login",
};

describe("readPublicConfig", () => {
  it("returns trimmed public identifiers", () => {
    expect(readPublicConfig({ ...valid, VITE_COGNITO_CLIENT_ID: " client " }).userPoolClientId).toBe("client");
  });

  it("fails fast when deployment output is missing", () => {
    expect(() => readPublicConfig({ ...valid, VITE_API_BASE_URL: "" })).toThrow("apiBaseUrl");
  });
});
