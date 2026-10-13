/**
 * useGuideRun: a failing status read must be visible, not look like "no run yet".
 */
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useGuideRun } from "./useGuideRun";

const getLatestRun = vi.fn();

vi.mock("@/services", () => ({
  getServices: () => ({ run: { getLatestRun } }),
}));

beforeEach(() => {
  getLatestRun.mockReset();
});

describe("useGuideRun", () => {
  it("reports an error, and stays unloaded, when the first read fails", async () => {
    getLatestRun.mockRejectedValue(new Error("network"));

    const { result } = renderHook(() => useGuideRun("room", "discovery", true));

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.loaded).toBe(false);
    expect(result.current.run).toBeNull();
  });

  it("clears the error once a later read succeeds", async () => {
    getLatestRun
      .mockRejectedValueOnce(new Error("blip"))
      .mockResolvedValue({ status: "running", phase: "asking_guide" });

    const { result } = renderHook(() => useGuideRun("room", "discovery", true));

    await waitFor(() => expect(result.current.error).not.toBeNull());
    act(() => result.current.refresh());
    await waitFor(() => expect(result.current.error).toBeNull());
    expect(result.current.loaded).toBe(true);
    expect(result.current.run?.status).toBe("running");
  });

  it("keeps the last good run when a later read fails", async () => {
    getLatestRun
      .mockResolvedValueOnce({ status: "running", phase: "posting" })
      .mockRejectedValue(new Error("blip"));

    const { result } = renderHook(() => useGuideRun("room", "discovery", true));
    await waitFor(() => expect(result.current.run?.status).toBe("running"));

    act(() => result.current.refresh());
    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.run?.status).toBe("running");
  });
});
