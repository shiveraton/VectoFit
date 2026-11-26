import type { Phase, Rep, SessionResult, SessionResultError, Side } from "./types";

export function scale(d0: number, d1: number, r0: number, r1: number) {
  return (value: number) => d0 === d1 ? r0 : r0 + ((value - d0) / (d1 - d0)) * (r1 - r0);
}

export function yMaxOf(peaks: readonly (number | null)[]): number {
  const finite = peaks.filter((value): value is number => value !== null && Number.isFinite(value));
  return Math.max(12, Math.ceil(Math.max(0, ...finite.map(Math.abs)) / 6) * 6);
}

export function yTicks(yMax: number, signed = false): [number, number, number] {
  return signed ? [-yMax, 0, yMax] : [0, yMax / 2, yMax];
}

export function balanceFillPct(balanceDeg: number | null, yMax: number): number | null {
  if (balanceDeg === null || !Number.isFinite(balanceDeg) || !Number.isFinite(yMax) || yMax <= 0) return null;
  return Math.min(Math.abs(balanceDeg), yMax) / yMax * 50;
}

function kneeCount(result: SessionResult, side: Side, status: "deviated" | "borderline"): number {
  return result.reps.filter(rep => rep.status !== "unassessable" && rep.kneeStatus[side] === status).length;
}

export function selectFocusSide(result: SessionResult): Side {
  let left = kneeCount(result, "left", "deviated");
  let right = kneeCount(result, "right", "deviated");
  // TODO(decision-11): With no deviations, use borderline counts to avoid reporting zero affected reps.
  if (left === 0 && right === 0) {
    left = kneeCount(result, "left", "borderline");
    right = kneeCount(result, "right", "borderline");
  }
  if (left !== right) return left > right ? "left" : "right";
  // TODO(decision-11): Exact count and peak ties use left for deterministic copy.
  return (result.summary.right.worstPeakDeg ?? -Infinity) > (result.summary.left.worstPeakDeg ?? -Infinity) ? "right" : "left";
}

export function selectTier(result: SessionResult) {
  const { counts, assessableReps } = result.summary;
  if (assessableReps === 0) return { kind: "empty", label: "", headline: "We couldn't assess any reps" } as const;
  if (counts.aligned === assessableReps) return { kind: "all_aligned", label: "All aligned", headline: result.presentation?.headline ?? "Clean set. Both knees tracked in line." } as const;
  const side = selectFocusSide(result);
  const count = kneeCount(result, side, "deviated") || kneeCount(result, side, "borderline");
  const reps = count === 1 ? "rep" : "reps";
  // TODO(decision-1): Presentation tiers use the handoff's default ratio, not angle cutoffs.
  if (counts.aligned / assessableReps >= 0.6) return {
    kind: "mostly_aligned", label: "Mostly aligned",
    headline: result.presentation?.headline ?? `Mostly solid. ${side === "left" ? "Left" : "Right"} knee drifted inward on ${count} ${reps}.`,
  } as const;
  return { kind: "needs_work", label: "Needs work",
    headline: result.presentation?.headline ?? `Your ${side} knee drifted inward on ${count} ${reps}. Let's tighten it up.` } as const;
}

export function selectComparison(result: SessionResult): string | null {
  const previous = result.summary.previousAlignedCount;
  if (previous === null) return null;
  const delta = result.summary.counts.aligned - previous;
  if (delta > 0) return `+${delta} aligned vs last set`;
  if (delta < 0) return `${Math.abs(delta)} fewer aligned vs last set`;
  return "Same as last set";
}

export function selectTracking(result: SessionResult) {
  const { assessableReps, totalReps } = result.summary;
  const ratio = totalReps > 0 ? assessableReps / totalReps : 0;
  // TODO(decision-1): These are the supplied presentation defaults for tracking coverage.
  const label = ratio >= 0.9 ? "Good" : ratio >= 0.7 ? "Fair" : "Limited";
  return { label, limited: label === "Limited", caption: totalReps > 0 && assessableReps === totalReps
    ? "All reps clearly visible" : `${assessableReps} of ${totalReps} reps tracked` };
}

export function phaseAtTime(rep: Rep, timeMs: number): Phase | null {
  // TODO(decision-5): Without recorded boundaries or a turning point, don't invent a phase.
  if (!rep.phases || rep.durationMs === null || !Number.isFinite(timeMs)) return null;
  const time = Math.max(0, Math.min(timeMs, rep.durationMs));
  if (time < rep.phases.descentEndMs) return "descent";
  if (time <= rep.phases.bottomEndMs) return "bottom";
  return "ascent";
}

export function interpolate(tMs: readonly number[], values: readonly number[], timeMs: number): number | null {
  if (!tMs.length || tMs.length !== values.length || !Number.isFinite(timeMs)) return null;
  for (let i = 0; i < tMs.length; i++) {
    if (!Number.isFinite(tMs[i]) || !Number.isFinite(values[i]) || (i > 0 && tMs[i] <= tMs[i - 1])) return null;
  }
  if (timeMs <= tMs[0]) return values[0];
  for (let i = 1; i < tMs.length; i++) {
    if (timeMs <= tMs[i]) return scale(tMs[i - 1], tMs[i], values[i - 1], values[i])(timeMs);
  }
  return values[values.length - 1];
}

export function mirrorX(x: number, mirrored: boolean): number {
  return mirrored ? x : 1 - x;
}

export function selectDefaultRep(result: SessionResult): Rep | null {
  const assessable = result.reps.filter(rep => rep.status !== "unassessable");
  if (!assessable.length) return result.reps[0] ?? null;
  if (assessable.every(rep => rep.status === "aligned")) return assessable[0];
  return assessable.reduce((worst, rep) =>
    (rep.worstPeakDeg === null ? -Infinity : Math.abs(rep.worstPeakDeg)) > (worst.worstPeakDeg === null ? -Infinity : Math.abs(worst.worstPeakDeg)) ? rep : worst);
}

export function selectUnassessableCopy(rep: Rep) {
  if (rep.reasonDetail) return { title: "We couldn't assess this rep.", body: rep.reasonDetail };
  if (rep.reason === "knee_out_of_frame") return {
    title: "We couldn't assess this rep. Your knee left the frame.",
    body: "We couldn't see both knees clearly in this rep, so we left it out of your results.",
  };
  return { title: "We couldn't assess this rep.", body: rep.reason === "rep_not_segmentable"
    ? "We couldn't tell where this rep started and ended, so we left it out of your results."
    : "The camera couldn't track your knees reliably here, so we left it out of your results." };
}

export function selectInsight(rep: Rep): string | null {
  if (rep.modelEvidence?.disagrees) return null;
  if (rep.insight !== undefined) return rep.insight;
  if (rep.status === "unassessable") return selectUnassessableCopy(rep).body;
  if (rep.status === "aligned") return "Both knees stayed in line through this rep.";
  const phase = rep.peakAtMs === null ? null : phaseAtTime(rep, rep.peakAtMs);
  if (!rep.worseKnee || !phase) return null;
  return rep.status === "borderline"
    ? `Your ${rep.worseKnee} knee drifted slightly inward during the ${phase}.`
    : `Your ${rep.worseKnee} knee moved inward most during the ${phase}.`;
}

export function selectBalanceCaption(balanceDeg: number | null): string | null {
  if (balanceDeg === null || !Number.isFinite(balanceDeg)) return null;
  if (balanceDeg === 0) return "Both knees even";
  return `${balanceDeg > 0 ? "Right" : "Left"} knee drifts ${Math.abs(balanceDeg)}° more`;
}

export function selectFocusCues(result: SessionResult): string[] {
  if (result.presentation) return result.presentation.cues;
  if (!result.summary.assessableReps) return [];
  if (result.summary.counts.deviated || result.summary.counts.borderline) {
    // TODO(decision-4): Defer the optional 3-degree cue; the contract forbids UI angle thresholds.
    return ["Push your knees out over your toes on the way up."];
  }
  return ["Great alignment. Keep your knees tracking over your toes."];
}

export function selectErrorBody(error: SessionResultError): string {
  if (error.detail) return error.detail;
  if (error.kind === "network") return "Check your connection and try again.";
  // TODO(decision-8): Saved-data wording requires explicit evidence from the future backend adapter.
  if (error.kind === "processing_failed" && error.sessionSaved === true) {
    return "Your session data was saved. Try analyzing it again.";
  }
  return "Something went wrong. Try again.";
}
