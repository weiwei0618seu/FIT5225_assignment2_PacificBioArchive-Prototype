import { Amplify } from "aws-amplify";
import {
  confirmSignUp,
  fetchAuthSession,
  getCurrentUser,
  signIn,
  signInWithRedirect,
  signOut,
  signUp,
  type AuthUser,
} from "aws-amplify/auth";

import type { PublicConfig } from "../config";

export type Registration = {
  email: string;
  firstName: string;
  lastName: string;
  password: string;
};

export function configureAuth(config: PublicConfig): void {
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: config.userPoolId,
        userPoolClientId: config.userPoolClientId,
        signUpVerificationMethod: "code",
        loginWith: {
          oauth: {
            domain: config.cognitoDomain.replace(/^https?:\/\//, ""),
            scopes: ["openid", "email", "profile"],
            redirectSignIn: [config.oauthRedirectUri],
            redirectSignOut: [config.oauthLogoutUri],
            responseType: "code",
          },
        },
      },
    },
  });
}

export async function registerUser(values: Registration): Promise<void> {
  await signUp({
    username: values.email.trim().toLowerCase(),
    password: values.password,
    options: {
      userAttributes: {
        email: values.email.trim().toLowerCase(),
        given_name: values.firstName.trim(),
        family_name: values.lastName.trim(),
      },
    },
  });
}

export async function verifyUser(email: string, code: string): Promise<void> {
  await confirmSignUp({
    username: email.trim().toLowerCase(),
    confirmationCode: code.trim(),
  });
}

export async function loginUser(email: string, password: string): Promise<void> {
  await signIn({ username: email.trim().toLowerCase(), password });
}

export async function loginWithGoogle(): Promise<void> {
  await signInWithRedirect({ provider: "Google" });
}

export async function logoutUser(): Promise<void> {
  await signOut();
}

export async function currentUser(): Promise<AuthUser | null> {
  try {
    return await getCurrentUser();
  } catch {
    return null;
  }
}

export async function idToken(): Promise<string> {
  const session = await fetchAuthSession();
  const token = session.tokens?.idToken?.toString();
  if (!token) throw new Error("Your session has expired. Please sign in again.");
  return token;
}

export type { AuthUser };
