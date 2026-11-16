import type { PoseLandmark } from "../hooks/useCameraPoseScreen";

const FPPA_CUTOFF_DEGREES = 10;

export interface KneeAlignmentCue {
  key: string;
  message: string;
}

export function parseVoiceCommand(transcript: string): "start" | "stop" | null {
  const command = transcript.toLowerCase().replace(/[.!?,]/g, "").trim();
  if (command === "start" || command === "start session") return "start";
  if (command === "stop" || command === "stop session") return "stop";
  return null;
}

function signedFppa(
  landmarks: PoseLandmark[],
  indices: number[],
  width: number,
  height: number,
): number | null {
  const points = indices.map((index) => landmarks[index]);
  const missingEvidence = points.some((point) =>
    !point || point.visibility < 0.5 || !Number.isFinite(point.visibility) ||
    !Number.isFinite(point.x_coordinate) || !Number.isFinite(point.y_coordinate),
  );
  if (missingEvidence) return null;

  const [hip, knee, ankle, oppositeHip] = points.map((point) => ({
    x: point.x_coordinate * width,
    y: point.y_coordinate * height,
  }));
  const thigh = { x: knee.x - hip.x, y: knee.y - hip.y };
  const shank = { x: ankle.x - knee.x, y: ankle.y - knee.y };
  const denominator = Math.hypot(thigh.x, thigh.y) * Math.hypot(shank.x, shank.y);
  if (denominator === 0 || hip.x === oppositeHip.x) return null;

  const cosine = (thigh.x * shank.x + thigh.y * shank.y) / denominator;
  const degrees = Math.acos(Math.max(-1, Math.min(1, cosine))) * 180 / Math.PI;
  const lineX = ankle.y !== hip.y
    ? hip.x + (ankle.x - hip.x) * (knee.y - hip.y) / (ankle.y - hip.y)
    : hip.x;
  const inward = (knee.x - lineX) * Math.sign(oppositeHip.x - hip.x) > 0;
  return inward ? degrees : -degrees;
}

export function getKneeAlignmentCue(
  landmarks: PoseLandmark[],
  width: number,
  height: number,
): KneeAlignmentCue | null {
  if (
    landmarks.length !== 33 || !Number.isFinite(width) || !Number.isFinite(height) ||
    width <= 0 || height <= 0
  ) return null;

  const left = signedFppa(landmarks, [23, 25, 27, 24], width, height);
  const right = signedFppa(landmarks, [24, 26, 28, 23], width, height);
  if (left === null || right === null) return null;

  const leftDirection = Math.abs(left) > FPPA_CUTOFF_DEGREES ? Math.sign(left) : 0;
  const rightDirection = Math.abs(right) > FPPA_CUTOFF_DEGREES ? Math.sign(right) : 0;
  if (!leftDirection && !rightDirection) return null;

  const both = leftDirection !== 0 && leftDirection === rightDirection;
  const side = Math.abs(left) >= Math.abs(right) ? "left" : "right";
  const direction = both ? leftDirection : side === "left" ? leftDirection : rightDirection;
  const movement = direction > 0 ? "caving in" : "drifting out";
  return {
    key: `${both ? "both" : side}-${direction > 0 ? "inward" : "outward"}`,
    message: both
      ? `Your knees are ${movement}. Keep both knees tracking over your feet.`
      : `Your ${side} knee is ${movement}. Keep your ${side} knee tracking over your ${side} foot.`,
  };
}
