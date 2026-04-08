import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";

import DocumentPicker from "../components/upload/DocumentPicker";
import { listDocuments, searchDocuments } from "../services/api";

vi.mock("../services/api", () => ({
  listDocuments: vi.fn(),
  searchDocuments: vi.fn(),
}));

describe("DocumentPicker", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("loads existing documents and emits selected document", async () => {
    listDocuments.mockResolvedValue({
      data: [
        { id: "doc-a", filename: "alpha.txt" },
        { id: "doc-b", filename: "beta.txt" },
      ],
    });

    const onSelect = vi.fn();
    render(<DocumentPicker value="" onSelect={onSelect} />);

    expect(await screen.findByText("alpha.txt")).toBeInTheDocument();

    const radios = screen.getAllByRole("radio");
    fireEvent.click(radios[1]);

    expect(onSelect).toHaveBeenCalledWith({ id: "doc-b", filename: "beta.txt" });
  });

  it("uses search endpoint when query is provided", async () => {
    listDocuments.mockResolvedValue({ data: [] });
    searchDocuments.mockResolvedValue({ data: [{ id: "doc-z", filename: "zeta.pdf" }] });

    render(<DocumentPicker value="" onSelect={vi.fn()} />);

    await screen.findByPlaceholderText("Search by filename");

    fireEvent.change(screen.getByPlaceholderText("Search by filename"), { target: { value: "zeta" } });
    fireEvent.click(screen.getByRole("button", { name: "Find" }));

    await waitFor(() => {
      expect(searchDocuments).toHaveBeenCalledWith("zeta", 100);
    });
  });
});
