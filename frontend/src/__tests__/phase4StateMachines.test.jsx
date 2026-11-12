import React from "react";
import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import QuickChat from "../pages/QuickChat";
import ComparePage from "../pages/ComparePage";
import DocumentUpload from "../components/upload/DocumentUpload";
import CompareEvaluationTab from "../components/compare/CompareEvaluationTab";
import ConfigWizard from "../components/config/ConfigWizard";
import DocumentPicker from "../components/upload/DocumentPicker";
import { SessionProvider, useSession } from "../hooks/useSession";
import { useDocument } from "../hooks/useDocument";
import * as api from "../services/api";

vi.mock("../services/api", async () => {
  const original = await vi.importActual("../services/api");
  return {
    ...original,
    listDocuments: vi.fn().mockResolvedValue({ data: [] }),
    searchDocuments: vi.fn().mockResolvedValue({ data: [] }),
    deleteDocument: vi.fn(),
    bulkDeleteDocuments: vi.fn(),
    clearAllDocuments: vi.fn(),
    getChunks: vi.fn(),
    applyBestPreset: vi.fn(),
    prepareChatSession: vi.fn(),
    getIndexStatus: vi.fn(),
    saveConfig: vi.fn(),
    compareIndex: vi.fn(),
  };
});

describe("Phase 4 frontend state machine & race fixes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("Fix #15a: QuickChat stops polling immediately on unmount and prevents double start", async () => {
    vi.useFakeTimers();
    localStorage.setItem(
      "rag_lab_session_v2",
      JSON.stringify({ docId: "doc-1", docIds: ["doc-1"], filename: "doc.pdf" }),
    );
    api.applyBestPreset.mockResolvedValue({ data: { id: "cfg-1" } });
    api.prepareChatSession.mockResolvedValue({ data: { job_id: "job-1" } });
    api.getIndexStatus.mockResolvedValue({ data: { status: "indexing", progress_pct: 25 } });

    const { unmount } = render(
      <SessionProvider>
        <QuickChat />
      </SessionProvider>,
    );

    const startButton = screen.getByRole("button", { name: /Start Chat/i });
    fireEvent.click(startButton);
    fireEvent.click(startButton);

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(api.applyBestPreset).toHaveBeenCalledTimes(1);
    expect(api.prepareChatSession).toHaveBeenCalledTimes(1);
    const pollsBeforeUnmount = api.getIndexStatus.mock.calls.length;
    expect(pollsBeforeUnmount).toBeGreaterThanOrEqual(1);

    unmount();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(api.getIndexStatus).toHaveBeenCalledTimes(pollsBeforeUnmount);
  });

  it("Fix #15b: useDocument.fetchChunks does not return MOCK_CHUNKS on empty or error", async () => {
    api.getChunks.mockResolvedValueOnce({ data: { chunks: [] } });
    const { result } = renderHook(() => useDocument());

    await act(async () => {
      await result.current.fetchChunks("doc-1", "cfg-1");
    });
    expect(result.current.chunks).toEqual([]);
    expect(result.current.error).toBeNull();

    api.getChunks.mockRejectedValueOnce(new Error("Backend 500"));
    await act(async () => {
      await result.current.fetchChunks("doc-1", "cfg-1");
    });
    expect(result.current.chunks).toEqual([]);
    expect(result.current.error).toContain("Backend 500");
  });

  it("Fix #15c: DocumentUpload handleClear clears only document keys, preserving mode and stagedConfigs", () => {
    localStorage.setItem(
      "rag_lab_session_v2",
      JSON.stringify({
        docId: "doc-1",
        docIds: ["doc-1"],
        configId: "cfg-1",
        filename: "spec.pdf",
        mode: "compare",
        stagedConfigs: [{ name: "Broad Recall" }],
        isQueryUnlocked: true,
      }),
    );

    let latestSession = null;
    function SessionSpy() {
      latestSession = useSession();
      return null;
    }

    render(
      <SessionProvider>
        <DocumentUpload onUpload={vi.fn()} onClear={vi.fn()} uploading={false} progress={0} />
        <SessionSpy />
      </SessionProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: /Upload a different file/i }));

    expect(latestSession.docId).toBeNull();
    expect(latestSession.docIds).toEqual([]);
    expect(latestSession.configId).toBeNull();
    expect(latestSession.filename).toBeNull();
    expect(latestSession.mode).toBe("compare");
    expect(latestSession.stagedConfigs).toEqual([{ name: "Broad Recall" }]);
  });

  it("Fix #16a: CompareEvaluationTab transitions empty -> populated without breaking hook order", () => {
    const { rerender } = render(<CompareEvaluationTab results={[]} onOpenEvaluationDetail={vi.fn()} />);
    expect(screen.getByText(/Run a comparison query/i)).toBeInTheDocument();

    rerender(
      <CompareEvaluationTab
        results={[
          {
            config: { name: "Config A", chunk_strategy: "fixed_size", top_k: 5 },
            latency_ms: 120,
            avg_similarity: 0.85,
            chunk_count: 3,
            evaluation: {
              answer_metrics: { faithfulness: 0.9, answer_relevancy: 0.85, context_recall: 0.8 },
              retrieval_metrics: { precision_at_k: 0.75, hit_rate_at_k: 1 },
            },
          },
        ]}
        onOpenEvaluationDetail={vi.fn()}
      />,
    );

    expect(screen.getByText("Comparative Metrics Matrix")).toBeInTheDocument();
    expect(screen.getAllByText("Config A").length).toBeGreaterThan(0);
  });

  it("Fix #16b: ConfigWizard guards handleComplete against double-submit", async () => {
    localStorage.setItem(
      "rag_lab_session_v2",
      JSON.stringify({ docId: "doc-1", docIds: ["doc-1"], filename: "notes.pdf" }),
    );
    localStorage.setItem("rag_lab_pipeline_config_v2", JSON.stringify({ step: 4 }));

    let resolveSave;
    api.saveConfig.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSave = resolve;
        }),
    );

    render(
      <MemoryRouter>
        <SessionProvider>
          <ConfigWizard />
        </SessionProvider>
      </MemoryRouter>,
    );

    const submitBtn = screen.getByRole("button", { name: /Build & Preview Pipeline/i });
    fireEvent.click(submitBtn);
    fireEvent.click(submitBtn);

    expect(api.saveConfig).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: /Saving Pipeline/i })).toBeDisabled();

    await act(async () => {
      resolveSave({ data: { id: "cfg-99" } });
    });
  });

  it("Fix #16c: DocumentPicker separates row deletion state from list refresh indicator", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    api.listDocuments.mockResolvedValue({
      data: [
        { id: "doc-a", filename: "alpha.txt" },
        { id: "doc-b", filename: "beta.txt" },
      ],
    });

    let resolveDelete;
    api.deleteDocument.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveDelete = resolve;
        }),
    );

    render(<DocumentPicker value="" onSelect={vi.fn()} />);

    expect(await screen.findByText("alpha.txt")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Delete alpha.txt" }));

    expect(api.deleteDocument).toHaveBeenCalledWith("doc-a");
    // Refresh label must NOT falsely switch to "Refreshing" just because a delete is in flight
    expect(screen.getByRole("button", { name: "Refresh" })).toBeDisabled();

    await act(async () => {
      resolveDelete({});
    });

    await waitFor(() => {
      expect(api.listDocuments).toHaveBeenCalledTimes(2);
    });
  });

  it("Fix #16d: ComparePage syncs stale isQueryUnlocked and unlocks custom staged configs after indexing", async () => {
    localStorage.setItem(
      "rag_lab_session_v2",
      JSON.stringify({
        docId: "doc-1",
        docIds: ["doc-1"],
        filename: "manual.pdf",
        stagedConfigs: [
          {
            name: "Custom Sparse",
            chunk_strategy: "fixed_size",
            chunk_params: { chunk_size: 512, overlap: 50 },
            embedding_provider: "nvidia",
            embedding_model: "nvidia/nemotron-3-embed-1b",
            retrieval_type: "sparse",
            top_k: 4,
            threshold: 0.2,
            indexingStatus: "idle",
          },
        ],
        isQueryUnlocked: true,
      }),
    );

    api.listDocuments.mockResolvedValue({ data: [{ id: "doc-1", filename: "manual.pdf" }] });
    api.compareIndex.mockResolvedValue({
      data: { status: "ready", collection_name: "nvidia_custom_sparse" },
    });

    render(
      <SessionProvider>
        <ComparePage />
      </SessionProvider>,
    );

    // Stale isQueryUnlocked=true with idle custom config must re-lock consistently
    const queryBox = await screen.findByPlaceholderText(/Run & Save Staged Configs/i);
    expect(queryBox).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: /Run & Save Staged Configs/i }));

    await waitFor(() => {
      expect(api.compareIndex).toHaveBeenCalledTimes(1);
    });

    const unlockedBox = await screen.findByPlaceholderText(/Enter your evaluation query/i);
    expect(unlockedBox).not.toBeDisabled();
  });
});
