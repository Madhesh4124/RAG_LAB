import React from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import { AuthProvider, useAuth } from "../hooks/useAuth";
import { notifyAuthExpired } from "../services/api";

vi.mock("../services/api", async () => {
  const original = await vi.importActual("../services/api");
  return {
    ...original,
    getMe: vi.fn().mockResolvedValue({ data: { id: "u1", username: "tester", is_admin: false } }),
  };
});

function AuthProbe() {
  const { isAuthenticated, loading, user } = useAuth();
  if (loading) return <div>loading</div>;
  return <div>{isAuthenticated ? `auth:${user.username}` : "anon"}</div>;
}

describe("AuthProvider 401 eviction sync", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("clears React user state when notifyAuthExpired is triggered", async () => {
    localStorage.setItem("raglab_token", "fake-token");
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    );

    expect(await screen.findByText("auth:tester")).toBeInTheDocument();

    act(() => {
      notifyAuthExpired();
    });

    await waitFor(() => {
      expect(localStorage.getItem("raglab_token")).toBeNull();
      expect(screen.getByText("anon")).toBeInTheDocument();
    });
  });
});
