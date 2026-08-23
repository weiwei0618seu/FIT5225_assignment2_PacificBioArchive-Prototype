export type PublicConfig = {
  region: string;
  apiBaseUrl: string;
  userPoolId: string;
  userPoolClientId: string;
  cognitoDomain: string;
  oauthRedirectUri: string;
  oauthLogoutUri: string;
};

type Environment = Record<string, string | boolean | undefined>;

export function isGoogleFederationEnabled(environment: Environment): boolean {
  const value = environment.VITE_ENABLE_GOOGLE_FEDERATION;
  return typeof value === "string" && value.trim().toLowerCase() === "true";
}

export function readPublicConfig(environment: Environment): PublicConfig {
  const required = {
    region: environment.VITE_AWS_REGION,
    apiBaseUrl: environment.VITE_API_BASE_URL,
    userPoolId: environment.VITE_COGNITO_USER_POOL_ID,
    userPoolClientId: environment.VITE_COGNITO_CLIENT_ID,
    cognitoDomain: environment.VITE_COGNITO_DOMAIN,
    oauthRedirectUri: environment.VITE_OAUTH_REDIRECT_URI,
    oauthLogoutUri: environment.VITE_OAUTH_LOGOUT_URI,
  };
  const missing = Object.entries(required)
    .filter(([, value]) => typeof value !== "string" || !value.trim())
    .map(([name]) => name);
  if (missing.length) {
    throw new Error(`Missing public configuration: ${missing.join(", ")}`);
  }
  return Object.fromEntries(
    Object.entries(required).map(([key, value]) => [key, String(value).trim()]),
  ) as PublicConfig;
}
