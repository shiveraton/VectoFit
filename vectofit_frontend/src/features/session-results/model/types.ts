export type Status = "aligned" | "borderline" | "deviated" | "unassessable";
export type Side = "left" | "right";
export type Phase = "descent" | "bottom" | "ascent";
export type ProcessingStage = "tracking" | "counting" | "checking";
export interface SessionResultError {
  kind: "processing_failed" | "network" | "unknown";
  sessionSaved?: boolean;
  detail?: string;
}
export type SessionResultState =
  | { status: "loading"; stage?: ProcessingStage }
  | { status: "error"; error: SessionResultError }
  | { status: "ready"; data: SessionResult };
export type UnassessableReason =
  | "knee_out_of_frame"
  | "low_tracking_confidence"
  | "rep_not_segmentable";

export type Landmark =
  | "nose"
  | "lShoulder"
  | "rShoulder"
  | "lHip"
  | "rHip"
  | "lKnee"
  | "rKnee"
  | "lAnkle"
  | "rAnkle";

export interface Rep {
  index: number;
  status: Status;
  kneeStatus: Record<Side, Status>;
  reason?: UnassessableReason;
  reasonDetail?: string;
  peakDeg: Record<Side, number> | null;
  worseKnee: Side | null;
  worstPeakDeg: number | null;
  peakAtMs: number | null;
  durationMs: number | null;
  phases: { descentEndMs: number; bottomEndMs: number } | null;
  series: { tMs: number[]; leftDeg: number[]; rightDeg: number[] } | null;
  offTrack: Partial<Record<Side, { startMs: number; endMs: number }>> | null;
  frames: { tMs: number; pts: Record<Landmark, [number, number]> }[] | null;
  kneeDirection?: Record<Side, "inward" | "outward" | null>;
  insight?: string | null;
  modelEvidence?: { label: "good" | "bad" | null; confidence: number | null; disagrees: boolean | null };
}

export interface SessionResult {
  sessionId: string;
  recordedAt: string;
  view: "front";
  capture: { mirrored: boolean | null; aspectRatio?: number | null };
  signedAngles?: boolean;
  presentation?: { headline: string; cues: string[]; modelDisagreement: boolean };
  summary: {
    totalReps: number;
    counts: Record<Status, number>;
    left: { status: Status; worstPeakDeg: number | null };
    right: { status: Status; worstPeakDeg: number | null };
    balanceDeg: number | null;
    assessableReps: number;
    previousAlignedCount: number | null;
  };
  reps: Rep[];
}
