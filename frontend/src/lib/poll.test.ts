import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import {
  POLL_DELAY_CAP_MS,
  POLL_DELAY_START_MS,
  POLL_TIMEOUT_MS,
  RUNS_LIST_LIMIT,
  isPendingStatus,
  isSettledStatus,
  nextPollDelayMs,
  pollUntilSettled,
} from "./poll.ts";

test("nextPollDelayMs is exponential and caps at 1s", () => {
  assert.equal(nextPollDelayMs(0), POLL_DELAY_START_MS);
  assert.equal(nextPollDelayMs(1), POLL_DELAY_CAP_MS);
  assert.equal(nextPollDelayMs(2), POLL_DELAY_CAP_MS);
  assert.equal(nextPollDelayMs(8), POLL_DELAY_CAP_MS);
  assert.ok(nextPollDelayMs(0) <= POLL_DELAY_CAP_MS);
});

test("COMPLETED is settled; QUEUED/RUNNING keep polling", () => {
  assert.equal(isPendingStatus("QUEUED"), true);
  assert.equal(isPendingStatus("RUNNING"), true);
  assert.equal(isPendingStatus("COMPLETED"), false);
  assert.equal(isSettledStatus("COMPLETED"), true);
  assert.equal(isSettledStatus("QUEUED"), false);
  assert.equal(isSettledStatus("RUNNING"), false);
  assert.equal(isSettledStatus(""), false);
  assert.equal(isSettledStatus(undefined), false);
});

test("pollUntilSettled stops on COMPLETED and does not keep fetching", async () => {
  const delays: number[] = [];
  let fetches = 0;
  const result = await pollUntilSettled({
    ids: ["a"],
    fetchRows: async () => {
      fetches += 1;
      return [{ run_id: "a", status: fetches >= 2 ? "COMPLETED" : "QUEUED" }];
    },
    sleep: async (ms) => {
      delays.push(ms);
    },
    now: () => 0,
  });
  assert.equal(result.settled, true);
  assert.equal(result.rows[0]?.status, "COMPLETED");
  assert.equal(fetches, 2);
  assert.deepEqual(delays, [POLL_DELAY_START_MS]);
});

test("pollUntilSettled sweep waits until every id is COMPLETED", async () => {
  let tick = 0;
  const result = await pollUntilSettled({
    ids: ["a", "b", "c"],
    fetchRows: async () => {
      tick += 1;
      return [
        { run_id: "a", status: tick >= 1 ? "COMPLETED" : "QUEUED" },
        { run_id: "b", status: tick >= 2 ? "COMPLETED" : "QUEUED" },
        { run_id: "c", status: tick >= 3 ? "COMPLETED" : "RUNNING" },
      ];
    },
    sleep: async () => {},
    now: () => 0,
  });
  assert.equal(result.settled, true);
  assert.equal(tick, 3);
  assert.ok(result.rows.every((row) => row.status === "COMPLETED"));
});

test("pollUntilSettled returns honest timeout at 45s without treating QUEUED as done", async () => {
  let now = 0;
  let fetches = 0;
  let timeouts = 0;
  const result = await pollUntilSettled({
    ids: ["stuck"],
    timeoutMs: POLL_TIMEOUT_MS,
    fetchRows: async () => {
      fetches += 1;
      return [{ run_id: "stuck", status: "QUEUED" }];
    },
    sleep: async (ms) => {
      now += ms;
    },
    now: () => now,
    onTimeout: () => {
      timeouts += 1;
    },
  });
  assert.equal(result.settled, false);
  assert.equal(result.rows[0]?.status, "QUEUED");
  assert.equal(timeouts, 1);
  assert.ok(now >= POLL_TIMEOUT_MS);
  assert.ok(fetches >= 2);
  assert.ok(fetches < 200);
});

test("continueAfterTimeout keeps polling until COMPLETED after the 45s error", async () => {
  let now = 0;
  let fetches = 0;
  let timeouts = 0;
  const result = await pollUntilSettled({
    ids: ["late"],
    continueAfterTimeout: true,
    fetchRows: async () => {
      fetches += 1;
      assert.ok(fetches < 200, "poll must stop after COMPLETED");
      return [{ run_id: "late", status: timeouts >= 1 ? "COMPLETED" : "QUEUED" }];
    },
    sleep: async (ms) => {
      now += ms;
    },
    now: () => now,
    onTimeout: () => {
      timeouts += 1;
    },
  });
  assert.equal(result.settled, true);
  assert.equal(timeouts, 1);
  assert.equal(result.rows[0]?.status, "COMPLETED");
  assert.ok(now >= POLL_TIMEOUT_MS);
});

test("runs list limit stays at last 20", () => {
  assert.equal(RUNS_LIST_LIMIT, 20);
});

test("next.config must not rewrite /api/v1 past the App proxy", () => {
  const here = dirname(fileURLToPath(import.meta.url));
  const src = readFileSync(join(here, "../../next.config.ts"), "utf8");
  assert.match(src, /Do NOT rewrite \/api\/v1/);
  assert.doesNotMatch(src, /rewrites\s*[:=]/);
  assert.doesNotMatch(src, /async\s+rewrites/);
  assert.doesNotMatch(src, /destination\s*:/);
});
