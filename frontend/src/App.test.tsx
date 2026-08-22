import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppRoutes } from "./App";
import * as authClient from "./auth/authClient";

vi.mock("./auth/authClient", async () => {
  const actual = await vi.importActual<typeof import("./auth/authClient")>("./auth/authClient");
  return {
    ...actual,
    currentUser: vi.fn(),
    loginUser: vi.fn(),
    loginWithGoogle: vi.fn(),
    logoutUser: vi.fn(),
    registerUser: vi.fn(),
    verifyUser: vi.fn(),
  };
});

function renderAt(path: string) {
  return render(
    <MemoryRouter
      initialEntries={[path]}
      future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
    >
      <AppRoutes />
    </MemoryRouter>,
  );
}

describe("authentication UI", () => {
  beforeEach(() => {
    vi.mocked(authClient.currentUser).mockResolvedValue(null);
  });

  it("redirects an unauthenticated protected route to login", async () => {
    renderAt("/");
    expect(await screen.findByRole("heading", { name: /sign in to your archive/i })).toBeInTheDocument();
  });

  it("submits native sign in and enters the protected shell", async () => {
    const user = userEvent.setup();
    vi.mocked(authClient.currentUser)
      .mockResolvedValueOnce(null)
      .mockResolvedValue({ username: "student@example.edu", userId: "user-1" });
    renderAt("/login");
    await user.type(screen.getByLabelText("Email"), "Student@Example.edu");
    await user.type(screen.getByLabelText("Password"), "ValidPass!123");
    await user.click(screen.getByRole("button", { name: /^sign in$/i }));
    await waitFor(() => expect(authClient.loginUser).toHaveBeenCalledWith("Student@Example.edu", "ValidPass!123"));
    expect(await screen.findByRole("heading", { name: /archive overview/i })).toBeInTheDocument();
  });

  it("registers all assignment fields then shows email verification", async () => {
    const user = userEvent.setup();
    renderAt("/register");
    await user.type(screen.getByLabelText("First name"), "Asha");
    await user.type(screen.getByLabelText("Last name"), "Nguyen");
    await user.type(screen.getByLabelText("Email"), "asha@example.edu");
    await user.type(screen.getByLabelText("Password"), "ValidPass!123");
    await user.click(screen.getByRole("button", { name: /create account/i }));
    expect(authClient.registerUser).toHaveBeenCalledWith({
      firstName: "Asha",
      lastName: "Nguyen",
      email: "asha@example.edu",
      password: "ValidPass!123",
    });
    expect(await screen.findByRole("heading", { name: /verify your email/i })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveValue("asha@example.edu");
  });

  it("starts Cognito Google federation", async () => {
    const user = userEvent.setup();
    renderAt("/login");
    await user.click(screen.getByRole("button", { name: /continue with google/i }));
    expect(authClient.loginWithGoogle).toHaveBeenCalledOnce();
  });

  it("logs an authenticated user out", async () => {
    const user = userEvent.setup();
    vi.mocked(authClient.currentUser).mockResolvedValue({ username: "student", userId: "user-1" });
    renderAt("/");
    await user.click(await screen.findByRole("button", { name: /log out/i }));
    expect(authClient.logoutUser).toHaveBeenCalledOnce();
    expect(await screen.findByRole("heading", { name: /sign in to your archive/i })).toBeInTheDocument();
  });
});
