/**
 * Background 202 / sweep polling.
 * Exponential delay capped at 1s. Stop when COMPLETED. Honest error at 45s.
 */

export const POLL_TIMEOUT_MS = 45_000;
export const POLL_DELAY_START_MS = 500;
export const POLL_DELAY_CAP_MS = 1_000;
export const RUNS_LIST_LIMIT = 20;

export function isPendingStatus(status?: string | null): boolean {
  return status === "QUEUED" || status === "RUNNING";
}

/** Terminal for the UI poller. COMPLETED is the happy stop; other non-pending statuses also halt. */
export function isSettledStatus(status?: string | null): boolean {
  if (!status) return false;
  if (status === "COMPLETED") return true;
  return !isPendingStatus(status);
}

/** 500ms, 1000ms, 1000ms, … */
export function nextPollDelayMs(attempt: number): number {
  const exp = POLL_DELAY_START_MS * 2 ** Math.max(0, attempt);
  return Math.min(POLL_DELAY_CAP_MS, exp);
}

export type PollRow = { run_id: string; status?: string | null };

export async function pollUntilSettled<T extends PollRow>(options: {
  ids: string[];
  fetchRows: (ids: string[]) => Promise<T[]>;
  timeoutMs?: number;
  /** Keep polling after the honest 45s error so the page can still settle. */
  continueAfterTimeout?: boolean;
  sleep?: (ms: number) => Promise<void>;
  now?: () => number;
  isCancelled?: () => boolean;
  onTick?: (rows: T[]) => void;
  onTimeout?: () => void;
}): Promise<{ settled: boolean; rows: T[] }> {
  const ids = options.ids.filter(Boolean);
  if (!ids.length) return { settled: true, rows: [] };

  const timeoutMs = options.timeoutMs ?? POLL_TIMEOUT_MS;
  const sleep = options.sleep ?? ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  const now = options.now ?? Date.now;
  const started = now();
  let attempt = 0;
  let last: T[] = [];
  let timeoutNotified = false;

  while (true) {
    if (options.isCancelled?.()) return { settled: false, rows: last };

    last = await options.fetchRows(ids);
    options.onTick?.(last);

    const byId = new Map(last.map((row) => [row.run_id, row]));
    const allSettled =
      ids.every((id) => byId.has(id)) &&
      ids.every((id) => isSettledStatus(byId.get(id)?.status));

    if (allSettled) return { settled: true, rows: last };

    if (now() - started >= timeoutMs) {
      if (!timeoutNotified) {
        timeoutNotified = true;
        options.onTimeout?.();
      }
      if (!options.continueAfterTimeout) return { settled: false, rows: last };
    }

    await sleep(nextPollDelayMs(attempt));
    attempt += 1;
  }
}
