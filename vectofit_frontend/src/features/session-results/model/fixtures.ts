import type { Rep, SessionResult, Status } from "./types";
import { assertSessionResult } from "./validation";

export type FixtureName = "main" | "unassessable" | "all_aligned" | "zero_assessable" | "limited";

const peaks = [3, 2, 3, 4, 6, 4, 11, 8, 7, 3];
const statuses: Status[] = ["aligned", "aligned", "aligned", "aligned", "borderline", "aligned", "deviated", "deviated", "deviated", "aligned"];

function mainFixture(): SessionResult {
  const reps: Rep[] = peaks.map((peak, i) => ({
    index: i + 1,
    status: statuses[i],
    kneeStatus: { left: "aligned", right: statuses[i] },
    // TODO(decision-12): Unspecified fixture-only left peaks use min(3, supplied peak).
    peakDeg: { left: Math.min(3, peak), right: peak },
    worseKnee: "right",
    worstPeakDeg: peak,
    peakAtMs: null,
    durationMs: null,
    phases: null,
    series: null,
    offTrack: null,
    frames: null,
  }));
  Object.assign(reps[6], {
    durationMs: 2600,
    phases: { descentEndMs: 1205, bottomEndMs: 1595 },
    peakAtMs: 2200,
    series: {
      tMs: [0, 1400, 2000, 2200, 2600],
      // TODO(decision-12): Left samples stay within the specified 1–3 degree range.
      leftDeg: [1, 1, 2, 3, 2],
      rightDeg: [1, 3, 5, 11, 9],
    },
    offTrack: { right: { startMs: 2000, endMs: 2600 } },
    // TODO(decision-13): Complete normalized landmark frames were not supplied; leave unavailable.
  });
  return {
    sessionId: "fixture-main",
    // TODO(decision-12): A fixed synthetic date keeps development fixtures repeatable.
    recordedAt: "2026-01-01T00:00:00Z",
    view: "front",
    // TODO(decision-9): This fixture flag is not evidence of production capture mirroring.
    capture: { mirrored: true },
    summary: {
      totalReps: 10,
      counts: { aligned: 6, borderline: 1, deviated: 3, unassessable: 0 },
      left: { status: "aligned", worstPeakDeg: 3 },
      right: { status: "deviated", worstPeakDeg: 11 },
      balanceDeg: 8,
      assessableReps: 10,
      previousAlignedCount: 4,
    },
    reps,
  };
}

function unassessableRep(rep: Rep, reason: Rep["reason"]): Rep {
  return {
    ...rep, status: "unassessable", kneeStatus: { left: "unassessable", right: "unassessable" },
    reason, peakDeg: null, worseKnee: null, worstPeakDeg: null, peakAtMs: null,
    durationMs: null, phases: null, series: null, offTrack: null, frames: null,
  };
}

export function getSessionResultFixture(name: FixtureName): SessionResult {
  if (!__DEV__) throw new Error("Session result fixtures are available only in development.");
  const result = mainFixture();
  result.sessionId = `fixture-${name}`;
  if (name === "limited") {
    // TODO(decision-17): Exclude four existing sample reps to demonstrate limited tracking without new angles.
    result.reps = result.reps.map((rep, i) => i < 4 ? unassessableRep(rep, "low_tracking_confidence") : rep);
    result.summary.counts = { aligned: 2, borderline: 1, deviated: 3, unassessable: 4 };
    result.summary.assessableReps = 6;
  }
  if (name === "unassessable") {
    result.reps[6] = unassessableRep(result.reps[6], "knee_out_of_frame");
    result.summary.counts = { aligned: 6, borderline: 1, deviated: 2, unassessable: 1 };
    result.summary.right.worstPeakDeg = 8;
    result.summary.balanceDeg = 5;
    result.summary.assessableReps = 9;
  }
  if (name === "all_aligned") {
    // TODO(decision-12): Reuse the six supplied aligned reps instead of inventing new angles.
    result.reps = result.reps.filter(rep => rep.status === "aligned").map((rep, i) => ({ ...rep, index: i + 1 }));
    result.summary = {
      totalReps: 6, counts: { aligned: 6, borderline: 0, deviated: 0, unassessable: 0 },
      left: { status: "aligned", worstPeakDeg: 3 }, right: { status: "aligned", worstPeakDeg: 4 },
      balanceDeg: 1, assessableReps: 6, previousAlignedCount: null,
    };
  }
  if (name === "zero_assessable") {
    result.reps = result.reps.map(rep => unassessableRep(rep, "low_tracking_confidence"));
    result.summary = {
      totalReps: 10, counts: { aligned: 0, borderline: 0, deviated: 0, unassessable: 10 },
      left: { status: "unassessable", worstPeakDeg: null }, right: { status: "unassessable", worstPeakDeg: null },
      balanceDeg: null, assessableReps: 0, previousAlignedCount: null,
    };
  }
  assertSessionResult(result);
  return result;
}
