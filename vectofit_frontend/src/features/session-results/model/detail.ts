import { interpolate, mirrorX, scale } from "./selectors";
import type { Landmark, Rep, Side } from "./types";

export type PoseFrame = NonNullable<Rep["frames"]>[number];
export type ChartScale = (value: number) => number;

const landmarks: Landmark[] = ["nose", "lShoulder", "rShoulder", "lHip", "rHip", "lKnee", "rKnee", "lAnkle", "rAnkle"];

export function nearestFrame(rep: Rep, timeMs: number | null): PoseFrame | null {
  if (timeMs === null || !Number.isFinite(timeMs)) return null;
  const frames = rep.frames?.filter(frame => Number.isFinite(frame.tMs)) ?? [];
  if (!frames.length) return null;
  return frames.reduce((nearest, frame) => {
    const distance = Math.abs(frame.tMs - timeMs);
    const previous = Math.abs(nearest.tMs - timeMs);
    // TODO(decision-16): An exact timestamp tie selects the earlier stored frame.
    return distance < previous || (distance === previous && frame.tMs < nearest.tMs) ? frame : nearest;
  });
}

export function projectSkeleton(frame: PoseFrame | null, mirrored: boolean | null, aspectRatio = 1): Record<Landmark, [number, number]> | null {
  if (mirrored === null || !Number.isFinite(aspectRatio) || aspectRatio <= 0 || !frame?.pts || !landmarks.every(name => frame.pts[name]?.length === 2
    && frame.pts[name].every(value => Number.isFinite(value) && value >= 0 && value <= 1))) return null;
  const points = frame.pts;
  const shoulderY = (points.lShoulder[1] + points.rShoulder[1]) / 2;
  const ankleY = (points.lAnkle[1] + points.rAnkle[1]) / 2;
  const span = ankleY - shoulderY;
  if (span <= 0) return null;
  const factor = 130 / span;
  const hipX = (points.lHip[0] + points.rHip[0]) / 2;
  const hipY = (points.lHip[1] + points.rHip[1]) / 2;
  return Object.fromEntries(landmarks.map(name => {
    const [x, y] = points[name];
    return [name, [120 + (mirrorX(x, mirrored) - mirrorX(hipX, mirrored)) * factor * aspectRatio, 92 + (y - hipY) * factor]];
  })) as Record<Landmark, [number, number]>;
}

export function angleAtTime(rep: Rep, side: Side, timeMs: number | null): number | null {
  if (!rep.series || timeMs === null) return null;
  return interpolate(rep.series.tMs, side === "left" ? rep.series.leftDeg : rep.series.rightDeg, timeMs);
}

export function formatAngle(value: number | null): string {
  // TODO(decision-16): Interpolated readouts display tenths, without trailing .0.
  return value === null || !Number.isFinite(value) ? "—" : `${Number(value.toFixed(1))}°`;
}

export function timeScale(durationMs: number | null, width: number, gutter: number): ChartScale | null {
  if (durationMs === null || !Number.isFinite(durationMs) || durationMs <= 0 || width <= gutter * 2) return null;
  return scale(0, durationMs, gutter, width - gutter);
}

export function timeFromPosition(x: number, width: number, durationMs: number, gutter: number): number | null {
  const xScale = timeScale(durationMs, width, gutter);
  if (!xScale || !Number.isFinite(x)) return null;
  const time = scale(xScale(0), xScale(durationMs), 0, durationMs)(x);
  return Math.max(0, Math.min(durationMs, time));
}

export function seriesPath(
  times: readonly number[], values: readonly number[], xScale: ChartScale, yScale: ChartScale,
  window?: { startMs: number; endMs: number },
): string {
  if (!times.length || interpolate(times, values, times[0]) === null) return "";
  const start = Math.max(times[0], window?.startMs ?? times[0]);
  const end = Math.min(times[times.length - 1], window?.endMs ?? times[times.length - 1]);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return "";
  const startValue = interpolate(times, values, start);
  const endValue = interpolate(times, values, end);
  if (startValue === null || endValue === null) return "";
  const samples: [number, number][] = [[start, startValue]];
  for (let i = 0; i < times.length; i++) {
    if (times[i] > start && times[i] < end) samples.push([times[i], values[i]]);
  }
  if (end !== start) samples.push([end, endValue]);
  const points = samples.map(([time, value]) => [xScale(time), yScale(value)]);
  if (points.some(point => point.some(value => !Number.isFinite(value)))) return "";
  return points.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`).join(" ");
}

export function lineLabelPositions(leftY: number, rightY: number, height: number): Record<Side, number> {
  const clamp = (y: number) => Math.max(14, Math.min(height - 14, y));
  let left = clamp(leftY);
  let right = clamp(rightY);
  if (Math.abs(left - right) < 28) {
    const center = Math.max(28, Math.min(height - 28, (left + right) / 2));
    const leftFirst = left <= right;
    left = center + (leftFirst ? -14 : 14);
    right = center + (leftFirst ? 14 : -14);
  }
  return { left, right };
}
