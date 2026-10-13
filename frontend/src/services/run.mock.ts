/** Run progress — mock: the run has already finished. */
import type { RunProgress, RunService, RunType } from "./run.contract";

export class MockRunService implements RunService {
  async getLatestRun(
    _roomId: string,
    runType: RunType = "discovery",
  ): Promise<RunProgress | null> {
    return {
      id: "mock-run",
      runType,
      status: "completed",
      phase: "posting",
      elapsedSeconds: 8,
    };
  }

  subscribeProgress(
    _roomId: string,
    _onProgress: (run: RunProgress) => void,
    onLive: (live: boolean) => void,
  ): () => void {
    onLive(false); // nothing is pushed in mock mode; callers poll
    return () => {};
  }

  async startRun(): Promise<void> {}
}
