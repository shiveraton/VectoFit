import type { SessionResult, Side, Status } from "./types";

function invariant(condition: boolean, message: string): asserts condition {
  if (!condition) throw new Error(`Invalid session result: ${message}`);
}

export function assertSessionResult(result: SessionResult): void {
  const { summary, reps } = result;
  const statuses: Status[] = ["aligned", "borderline", "deviated", "unassessable"];
  invariant(summary.totalReps === reps.length, "total does not match repetitions");
  invariant(new Set(reps.map(rep => rep.index)).size === reps.length, "duplicate repetition index");
  for (const status of statuses) {
    invariant(Number.isInteger(summary.counts[status]) && summary.counts[status] >= 0, "invalid status count");
    invariant(summary.counts[status] === reps.filter(rep => rep.status === status).length, `${status} count mismatch`);
  }
  const assessable = reps.filter(rep => rep.status !== "unassessable");
  invariant(summary.assessableReps === assessable.length, "assessable count mismatch");
  for (const side of ["left", "right"] as Side[]) {
    const peaks = assessable.flatMap(rep => rep.peakDeg === null ? [] : [rep.peakDeg[side]]);
    const worstPeak = peaks.length ? peaks.reduce((worst, peak) => Math.abs(peak) > Math.abs(worst) ? peak : worst) : null;
    invariant(summary[side].worstPeakDeg === worstPeak, `${side} aggregate includes missing or excluded evidence`);
    if (!assessable.length) invariant(summary[side].status === "unassessable", `${side} has a status without evidence`);
  }
  const left = summary.left.worstPeakDeg;
  const right = summary.right.worstPeakDeg;
  if (left === null || right === null) invariant(summary.balanceDeg === null, "balance has missing evidence");
  else invariant(summary.balanceDeg !== null && Math.abs(summary.balanceDeg - (result.signedAngles ? Math.abs(right) - Math.abs(left) : right - left)) < 1e-9, "balance sign or value mismatch");

  for (const rep of reps) {
    invariant(Number.isInteger(rep.index) && rep.index > 0, "invalid repetition index");
    const missingKnee = rep.kneeStatus.left === "unassessable" || rep.kneeStatus.right === "unassessable";
    invariant(!missingKnee || rep.status === "unassessable", "missing knee marked assessable");
    if (rep.peakDeg) invariant(Object.values(rep.peakDeg).every(Number.isFinite), "non-finite knee peak");
    invariant(rep.worstPeakDeg === null || Number.isFinite(rep.worstPeakDeg), "non-finite worst peak");
    invariant(rep.durationMs === null || (Number.isFinite(rep.durationMs) && rep.durationMs > 0), "invalid duration");
    const validTime = (time: number) => Number.isFinite(time) && time >= 0 && (rep.durationMs === null || time <= rep.durationMs);
    invariant(rep.peakAtMs === null || validTime(rep.peakAtMs), "invalid peak time");
    if (rep.phases) invariant(validTime(rep.phases.descentEndMs) && validTime(rep.phases.bottomEndMs)
      && rep.phases.descentEndMs <= rep.phases.bottomEndMs, "invalid phase boundaries");
    if (rep.series) {
      const { tMs, leftDeg, rightDeg } = rep.series;
      invariant(tMs.length > 0 && tMs.length === leftDeg.length && tMs.length === rightDeg.length, "series length mismatch");
      invariant(tMs.every((time, i) => validTime(time) && (i === 0 || time > tMs[i - 1])), "unordered series times");
      invariant([...leftDeg, ...rightDeg].every(Number.isFinite), "non-finite series angle");
    }
    for (const window of Object.values(rep.offTrack ?? {})) {
      invariant(validTime(window.startMs) && validTime(window.endMs) && window.startMs <= window.endMs, "invalid off-track window");
    }
    for (const frame of rep.frames ?? []) {
      invariant(validTime(frame.tMs), "invalid landmark time");
      invariant(Object.values(frame.pts).every(point => point.every(value => Number.isFinite(value) && value >= 0 && value <= 1)), "landmark is not normalized");
    }
  }
}
