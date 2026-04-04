import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import App from "../App";

const mockAuthState = {
  isAuthenticated: false,
  loading: false,
  user: null,
  logout: vi.fn(),
};

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => mockAuthState,
}));

vi.mock("../services/api", async () => {
  const original = await vi.importActual("../services/api");
  return {
    ...original,
    listDocuments: vi.fn().mockResolvedValue({ data: [] }),
    searchDocuments: vi.fn().mockResolvedValue({ data: [] }),
    applyBestPreset: vi.fn().mockResolvedValue({ data: { id: "cfg-best" } }),
    uploadDocument: vi.fn().mockResolvedValue({ data: { id: "doc-1", filename: "doc.txt" } }),
  };
});

describe("App routing", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("redirects protected route to login when unauthenticated", async () => {
    window.history.pushState({}, "", "/setup");
    mockAuthState.isAuthenticated = false;
    mockAuthState.loading = false;

    render(<App />);

    expect(await screen.findByText("Sign in to continue")).toBeInTheDocument();
  });

  it("navigates mode select to chat when authenticated", async () => {
    const user = userEvent.setup();

    window.history.pushState({}, "", "/mode-select");
    mockAuthState.isAuthenticated = true;
    mockAuthState.loading = false;
    mockAuthState.user = { username: "tester" };

    render(<App />);

    await user.click(screen.getByRole("button", { name: "Chat mode" }));

    expect(
      await screen.findByText("Choose a document and start chatting with the best preset automatically applied."),
    ).toBeInTheDocument();
  });
});
