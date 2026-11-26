import { FONTS } from "../../../theme/fonts";

export const tokens = {
  color: {
    bg: "#0E1116",
    surface: "#141820",
    surfaceSubtle: "#1B202B",
    hairline: "rgba(255,255,255,.08)",
    primary: "#2DD4BF",
    primaryDim: "rgba(45,212,191,.12)",
    text: "#F1F5F9",
    textMuted: "#94A3B8",
    textSubtle: "#8A94A6",
    neutralLine: "#94A3B8",
    skeletonBody: "#CBD5E1",
    backdrop: "rgba(0,0,0,.65)",
  },
  status: {
    aligned: { fill: "#10B981", text: "#34D399" },
    borderline: { fill: "#F59E0B", text: "#FBBF24" },
    deviated: { fill: "#F43F5E", text: "#FB7185" },
    unassessable: { fill: "#64748B", text: "#8A94A6" },
  },
  font: {
    // TODO(decision-10): Keep bundled fonts until Manrope/Inter assets are supplied.
    display: FONTS.bold,
    text: FONTS.regular,
  },
  size: { screenPadding: 24, cardRadius: 16, pillRadius: 12, touch: 48, repWidth: 52, repHeight: 64,
    chartHeight: 144, chartGutter: 32 },
  type: { minimum: 12, maxFontSizeMultiplier: 1.3 },
  pressedOpacity: 0.7,
  motion: { countUpMs: 600, selectionScrollMs: 200, loadingMs: 1200 },
} as const;
