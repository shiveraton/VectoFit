import { StyleSheet } from "react-native";

export const CAMERA_COLORS = {
  background: "#0F172A",
  surface: "#1E293B",
  surfaceElevated: "#334155",
  border: "#334155",
  primary: "#F97316",
  danger: "#EF4444",
  text: "#F8FAFC",
  textSecondary: "#94A3B8",
  error: "#FCA5A5",
  black: "#000000",
  success: "#22C55E",
} as const;

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: CAMERA_COLORS.black,
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
    gap: 16,
    backgroundColor: CAMERA_COLORS.background,
  },
  permissionTitle: {
    color: CAMERA_COLORS.text,
    fontSize: 22,
    fontWeight: "800",
    textAlign: "center",
  },
  permissionText: {
    color: CAMERA_COLORS.textSecondary,
    fontSize: 14,
    lineHeight: 20,
    textAlign: "center",
  },

  // The preview owns the available height. Do not impose a minimum that can
  // force the camera and overlays beyond the usable screen on compact devices.
  cameraViewport: {
    flex: 1,
    minHeight: 0,
    position: "relative",
    overflow: "hidden",
    backgroundColor: CAMERA_COLORS.black,
  },

  // Top HUD: transparent and shallow so the subject remains visible.
  topOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    zIndex: 2,
    paddingHorizontal: 14,
    paddingTop: 10,
    gap: 9,
  },
  topOverlayCompact: {
    paddingTop: 6,
    gap: 7,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 10,
  },
  titleGroup: {
    flex: 1,
    gap: 3,
  },
  eyebrow: {
    color: "#FDBA74",
    fontSize: 9,
    fontWeight: "800",
    letterSpacing: 1.35,
    textTransform: "uppercase",
  },
  exerciseTitle: {
    color: CAMERA_COLORS.text,
    fontSize: 20,
    fontWeight: "800",
    letterSpacing: 0.1,
    textShadowColor: "rgba(0, 0, 0, 0.55)",
    textShadowRadius: 8,
    textShadowOffset: { width: 0, height: 1 },
  },
  exerciseTitleCompact: {
    fontSize: 18,
  },
  cameraFlipButton: {
    minWidth: 46,
    minHeight: 42,
    paddingHorizontal: 13,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 21,
    backgroundColor: "rgba(15, 23, 42, 0.56)",
    borderWidth: 1,
    borderColor: "rgba(248, 250, 252, 0.16)",
  },
  cameraFlipText: {
    color: CAMERA_COLORS.text,
    fontSize: 12,
    fontWeight: "700",
  },
  controlPressed: {
    opacity: 0.72,
  },
  controlDisabled: {
    opacity: 0.42,
  },

  // Tracking uses restrained status color rather than a large banner.
  trackingPill: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    minHeight: 28,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: "rgba(15, 23, 42, 0.62)",
    borderWidth: 1,
    borderColor: "rgba(226, 232, 240, 0.12)",
  },
  trackingPillReady: {
    backgroundColor: "rgba(20, 83, 45, 0.34)",
    borderColor: "rgba(74, 222, 128, 0.30)",
  },
  trackingPillWarning: {
    borderColor: "rgba(251, 146, 60, 0.28)",
  },
  trackingDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: CAMERA_COLORS.textSecondary,
  },
  trackingDotReady: {
    backgroundColor: "#4ADE80",
  },
  trackingDotWarning: {
    backgroundColor: "#FB923C",
  },
  trackingText: {
    color: "rgba(248, 250, 252, 0.94)",
    fontSize: 11,
    fontWeight: "600",
  },

  // Compact luminous feedback: subtle tint and border, never a large card.
  feedbackPill: {
    alignSelf: "flex-start",
    maxWidth: "92%",
    minHeight: 31,
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    paddingHorizontal: 11,
    paddingVertical: 7,
    borderRadius: 17,
    backgroundColor: "rgba(124, 45, 18, 0.48)",
    borderWidth: 1,
    borderColor: "rgba(251, 146, 60, 0.34)",
    shadowColor: "#F97316",
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.16,
    shadowRadius: 7,
    elevation: 2,
  },
  feedbackPillCompact: {
    minHeight: 29,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  feedbackGlow: {
    width: 5,
    height: 5,
    borderRadius: 3,
    backgroundColor: "#FDBA74",
  },
  feedbackText: {
    flexShrink: 1,
    color: "rgba(255, 247, 237, 0.96)",
    fontSize: 12,
    lineHeight: 16,
    fontWeight: "600",
    textShadowColor: "rgba(249, 115, 22, 0.14)",
    textShadowRadius: 4,
  },

  // Bottom HUD is intentionally short and translucent. Avoid a tall opaque dock.
  bottomOverlay: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 2,
    paddingHorizontal: 12,
    paddingTop: 22,
    paddingBottom: 10,
    gap: 8,
    backgroundColor: "rgba(15, 23, 42, 0.60)",
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    borderTopWidth: 1,
    borderColor: "rgba(248, 250, 252, 0.08)",
  },
  bottomOverlayCompact: {
    paddingHorizontal: 10,
    paddingTop: 17,
    paddingBottom: 6,
    gap: 6,
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
  },
  bottomHud: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  metricsRow: {
    flex: 1,
    minWidth: 0,
    flexDirection: "row",
    alignItems: "center",
    gap: 13,
  },
  repMetric: {
    minWidth: 44,
    gap: 1,
  },
  metricLabel: {
    color: "rgba(226, 232, 240, 0.68)",
    fontSize: 9,
    fontWeight: "800",
    letterSpacing: 1.1,
  },
  repValue: {
    color: "#FDBA74",
    fontSize: 29,
    lineHeight: 33,
    fontWeight: "800",
    fontVariant: ["tabular-nums"],
    textShadowColor: "rgba(249, 115, 22, 0.20)",
    textShadowRadius: 5,
  },
  repValueCompact: {
    fontSize: 26,
    lineHeight: 29,
  },
  metricDivider: {
    height: 31,
    width: 1,
    backgroundColor: "rgba(248, 250, 252, 0.16)",
  },
  timerMetric: {
    gap: 3,
  },
  timerValue: {
    color: CAMERA_COLORS.text,
    fontSize: 18,
    lineHeight: 23,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },

  primaryButton: {
    minHeight: 46,
    minWidth: 126,
    paddingHorizontal: 16,
    paddingVertical: 11,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    borderRadius: 14,
    backgroundColor: CAMERA_COLORS.primary,
    borderWidth: 1,
    borderColor: "rgba(255, 255, 255, 0.16)",
  },
  primaryButtonText: {
    color: CAMERA_COLORS.text,
    fontSize: 13,
    fontWeight: "800",
    letterSpacing: 0.1,
  },
  primaryButtonPressed: {
    opacity: 0.82,
    transform: [{ scale: 0.985 }],
  },
  primaryButtonDisabled: {
    opacity: 0.48,
  },
  endSessionButton: {
    backgroundColor: "rgba(127, 29, 29, 0.88)",
    borderColor: "rgba(248, 113, 113, 0.30)",
  },
  framingHint: {
    color: "rgba(226, 232, 240, 0.72)",
    fontSize: 11,
    lineHeight: 15,
    textAlign: "center",
    paddingHorizontal: 8,
  },
  errorPill: {
    alignSelf: "stretch",
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 7,
    backgroundColor: "rgba(127, 29, 29, 0.58)",
    borderWidth: 1,
    borderColor: "rgba(252, 165, 165, 0.28)",
  },
  errorMessage: {
    color: CAMERA_COLORS.error,
    fontSize: 12,
    lineHeight: 16,
    fontWeight: "600",
  },
  statusPill: {
    alignSelf: "center",
    maxWidth: "100%",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 14,
    backgroundColor: "rgba(15, 23, 42, 0.70)",
    borderWidth: 1,
    borderColor: "rgba(148, 163, 184, 0.20)",
  },
  statusText: {
    flexShrink: 1,
    color: "rgba(248, 250, 252, 0.88)",
    fontSize: 11,
    lineHeight: 15,
    textAlign: "center",
  },
  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 8,
    flexWrap: "wrap",
  },

  voiceCueToggle: {
    minHeight: 28,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 7,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: "rgba(15, 23, 42, 0.62)",
    borderWidth: 1,
    borderColor: "rgba(226, 232, 240, 0.14)",
  },

  voiceCueToggleActive: {
    backgroundColor: "rgba(124, 45, 18, 0.38)",
    borderColor: "rgba(249, 115, 22, 0.42)",
    shadowColor: "#F97316",
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.18,
    shadowRadius: 6,
    elevation: 2,
  },

  voiceCueDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "#64748B",
  },

  voiceCueDotActive: {
    backgroundColor: "#FDBA74",
  },

  voiceCueLabel: {
    color: "rgba(226, 232, 240, 0.72)",
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 0.8,
  },

  voiceCueLabelActive: {
    color: "#FDBA74",
  },
});

export default styles;
