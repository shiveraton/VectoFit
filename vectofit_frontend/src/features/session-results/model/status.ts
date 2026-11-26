import { tokens } from "../theme/tokens";
import type { Status } from "./types";

export type StatusIconName = "check" | "dash" | "arrowSW" | "eyeOff" | "warning";

export const STATUS = {
  aligned: { label: "Aligned", icon: "check", ...tokens.status.aligned, dashed: false },
  borderline: { label: "Borderline", icon: "dash", ...tokens.status.borderline, dashed: false },
  deviated: { label: "Deviated", icon: "arrowSW", ...tokens.status.deviated, dashed: false },
  unassessable: { label: "Unassessable", icon: "eyeOff", ...tokens.status.unassessable, dashed: true },
} as const satisfies Record<Status, {
  label: string;
  icon: StatusIconName;
  fill: string;
  text: string;
  dashed: boolean;
}>;
