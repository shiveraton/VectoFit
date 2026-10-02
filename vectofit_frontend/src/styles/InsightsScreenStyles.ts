import { StyleSheet } from "react-native";
import { FONTS } from "../theme/fonts";

export const COLORS = {
  // Brand Motifs
  primaryOrange: "#F97316",
  primaryOrangeDark: "#EA580C",
  primaryOrangeLight: "#FFEDD5",
  primaryOrangeGlow: "rgba(249, 115, 22, 0.15)",

  crimsonRed: "#EF4444",
  crimsonRedDark: "#DC2626",
  crimsonRedLight: "#FEE2E2",
  crimsonRedGlow: "rgba(239, 68, 68, 0.15)",

  // Grays / Zinc Backgrounds
  bgDark: "#09090B",
  cardBg: "#18181B",
  cardBorder: "#27272A",
  inputBg: "#27272A",
  inputBorder: "#3F3F46",

  // Text Colors
  textPrimary: "#FAFAFA",
  textSecondary: "#A1A1AA",
  textMuted: "#71717A",
  textDisabled: "#52525B",

  // Status Colors
  successGreen: "#10B981",
  successBg: "rgba(16, 185, 129, 0.12)",
  warningYellow: "#F59E0B",
  disabledBg: "#27272A",
  disabledText: "#71717A",

  // Biomechanics Module Accent Tokens
  jaaColor: "#F97316", // Joint Angle Analysis - Orange
  romColor: "#EF4444", // Range of Motion - Blue
  kvtColor: "#EF4444", // Kinematic Velocity Tracking - Emerald
  badColor: "#F97316", // Bilateral Asymmetry Detection - Crimson
};

export const SPACING = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
};

export const RADIUS = {
  sm: 6,
  md: 10,
  lg: 16,
  xl: 24,
  full: 9999,
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: COLORS.bgDark,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: SPACING.lg,
    paddingTop: SPACING.xl,
    paddingBottom: SPACING.xxxl,
  },

  // Screen Header
  headerContainer: {
    marginBottom: SPACING.xl,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  headerTextGroup: {
    flex: 1,
  },
  greetingSubtitle: {
    fontFamily: FONTS.regular,
    fontSize: 12,
    color: COLORS.textSecondary,
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 2,
  },
  userNameTitle: {
    fontFamily: FONTS.bold,
    fontSize: 24,
    fontWeight: "800",
    color: COLORS.textPrimary,
    letterSpacing: -0.5,
  },
  brandBadge: {
    backgroundColor: COLORS.primaryOrangeGlow,
    borderWidth: 1,
    borderColor: COLORS.primaryOrange,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.xs,
    borderRadius: RADIUS.full,
  },
  brandBadgeText: {
    color: COLORS.primaryOrange,
    fontFamily: FONTS.bold,
    fontSize: 11,
    letterSpacing: 0.5,
    textTransform: "uppercase",
  },

  // Generic Card
  card: {
    fontFamily: FONTS.semiBold,
    backgroundColor: COLORS.cardBg,
    borderRadius: RADIUS.lg,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    padding: SPACING.lg,
    marginBottom: SPACING.xl,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },

  // Module Specific Card Borders
  cardJAA: {
    borderLeftWidth: 4,
    borderLeftColor: COLORS.jaaColor,
  },
  cardROM: {
    borderLeftWidth: 4,
    borderLeftColor: COLORS.romColor,
  },
  cardKVT: {
    borderLeftWidth: 4,
    borderLeftColor: COLORS.kvtColor,
  },
  cardBAD: {
    borderLeftWidth: 4,
    borderLeftColor: COLORS.badColor,
  },

  // Header inside Cards
  cardHeaderRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: SPACING.md,
  },
  cardTitle: {
    fontFamily: FONTS.bold,
    fontSize: 17,
    fontWeight: "700",
    color: COLORS.textPrimary,
    letterSpacing: -0.2,
  },

  // Hero Overview Highlight Box
  scoreHighlightCard: {
    backgroundColor: COLORS.primaryOrangeGlow,
    borderRadius: RADIUS.md,
    paddingVertical: SPACING.md,
    paddingHorizontal: SPACING.lg,
    alignItems: "center",
    marginBottom: SPACING.lg,
    borderWidth: 1,
    borderColor: COLORS.primaryOrange,
  },
  scoreHighlightLabel: {
    color: COLORS.primaryOrange,
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 2,
  },
  scoreHighlightValue: {
    color: COLORS.textPrimary,
    fontSize: 34,
    fontWeight: "900",
    fontVariant: ["tabular-nums"],
  },
  scoreHighlightSubtext: {
    color: COLORS.textSecondary,
    fontSize: 12,
    marginTop: 2,
  },

  // Metric Rows
  metricRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: SPACING.sm + 2,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.cardBorder,
  },
  metricRowLast: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: SPACING.sm + 2,
  },
  metricLabel: {
    color: COLORS.textSecondary,
    fontSize: 14,
    fontWeight: "500",
  },

  // Specific Metric Values
  metricValue: {
    color: COLORS.textPrimary,
    fontSize: 15,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },
  metricValueJAA: {
    color: COLORS.jaaColor,
    fontSize: 15,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },
  metricValueROM: {
    color: COLORS.romColor,
    fontSize: 15,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },
  metricValueKVT: {
    color: COLORS.kvtColor,
    fontSize: 15,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },
  metricValueBAD: {
    color: COLORS.badColor,
    fontSize: 15,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },

  // Diagnostics Box
  diagnosticBox: {
    marginTop: SPACING.md,
    padding: SPACING.md,
    backgroundColor: COLORS.inputBg,
    borderRadius: RADIUS.md,
    borderWidth: 1,
    borderColor: COLORS.inputBorder,
  },
  diagnosticLabel: {
    color: COLORS.textSecondary,
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    marginBottom: 4,
  },
  diagnosticBullet: {
    color: COLORS.textPrimary,
    fontSize: 13,
    fontWeight: "500",
    marginVertical: 2,
  },

  // Longitudinal Trends
  trendRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: SPACING.sm + 2,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.cardBorder,
  },
  trendFeature: {
    color: COLORS.textPrimary,
    fontSize: 14,
    fontWeight: "500",
  },
  trendImproved: {
    color: COLORS.successGreen,
    fontSize: 14,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },
  trendDeclined: {
    color: COLORS.crimsonRed,
    fontSize: 14,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },

  // Module Badges inside Card Header
  moduleBadge: {
    paddingHorizontal: SPACING.sm,
    paddingVertical: 2,
    borderRadius: RADIUS.sm,
  },
  badgeJAA: {
    backgroundColor: COLORS.primaryOrangeGlow,
  },
  badgeROM: {
    backgroundColor: "rgba(59, 130, 246, 0.15)",
  },
  badgeKVT: {
    backgroundColor: COLORS.successBg,
  },
  badgeBAD: {
    backgroundColor: COLORS.crimsonRedGlow,
  },
  moduleBadgeText: {
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 0.5,
  },
});

export default styles;
