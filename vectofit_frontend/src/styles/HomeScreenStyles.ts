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

  // Biomechanics Module Colors
  jaaColor: "#F97316", // Joint Angle Analysis - Orange
  romColor: "#3B82F6", // Range of Motion - Blue
  kvtColor: "#10B981", // Kinematic Velocity Tracking - Emerald
  badColor: "#EF4444", // Bilateral Asymmetry Detection - Crimson
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
  parentContainer: {
    flex: 1,
    backgroundColor: "#fff",
  },
  childContainer: {
    backgroundColor: "#fff",
  },
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

  // Welcome Header Section
  headerContainer: {
    marginBottom: SPACING.xl,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  headerTextGroup: {
    flex: 1,
    fontFamily: FONTS.bold,
  },
  greetingSubtitle: {
    fontFamily: FONTS.bold,
    fontSize: 14,
    color: COLORS.textSecondary,
    textTransform: "uppercase",
    letterSpacing: 1,
    marginBottom: 4,
  },
  userNameTitle: {
    fontSize: 26,
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
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 0.5,
  },

  // Generic Card Base
  card: {
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

  // Physical Info Card Header & Status
  cardHeaderRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: SPACING.lg,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: COLORS.textPrimary,
  },
  statusChip: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.xs,
    borderRadius: RADIUS.full,
    borderWidth: 1,
  },
  statusChipCalibrated: {
    backgroundColor: COLORS.successBg,
    borderColor: COLORS.successGreen,
  },
  statusChipUncalibrated: {
    backgroundColor: COLORS.crimsonRedGlow,
    borderColor: COLORS.crimsonRed,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  statusDotCalibrated: {
    backgroundColor: COLORS.successGreen,
  },
  statusDotUncalibrated: {
    backgroundColor: COLORS.crimsonRed,
  },
  statusText: {
    fontSize: 12,
    fontWeight: "600",
  },
  statusTextCalibrated: {
    color: COLORS.successGreen,
  },
  statusTextUncalibrated: {
    color: COLORS.crimsonRed,
  },

  // Physical Info Fields
  inputsGrid: {
    flexDirection: "row",
    gap: SPACING.md,
    marginBottom: SPACING.lg,
  },
  inputCol: {
    flex: 1,
  },
  inputLabel: {
    fontSize: 12,
    fontWeight: "600",
    color: COLORS.textSecondary,
    marginBottom: 6,
    textTransform: "uppercase",
  },
  textInput: {
    backgroundColor: COLORS.inputBg,
    borderWidth: 1,
    borderColor: COLORS.inputBorder,
    borderRadius: RADIUS.md,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
    fontSize: 16,
    fontWeight: "600",
    color: COLORS.textPrimary,
  },

  // BMI Banner
  bmiDisplayCard: {
    backgroundColor: COLORS.inputBg,
    borderRadius: RADIUS.md,
    padding: SPACING.md,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: SPACING.lg,
    borderLeftWidth: 4,
    borderLeftColor: COLORS.primaryOrange,
  },
  bmiLabelGroup: {
    flex: 1,
  },
  bmiLabel: {
    fontSize: 12,
    fontWeight: "700",
    color: COLORS.textSecondary,
    textTransform: "uppercase",
  },
  bmiSubtext: {
    fontSize: 11,
    color: COLORS.textMuted,
    marginTop: 2,
  },
  bmiValue: {
    fontSize: 22,
    fontWeight: "800",
    color: COLORS.primaryOrange,
  },

  // User Friendly Info Callout Box
  infoBox: {
    backgroundColor: "rgba(255, 255, 255, 0.03)",
    borderWidth: 1,
    borderColor: "rgba(255, 255, 255, 0.08)",
    borderRadius: RADIUS.md,
    padding: SPACING.md,
  },
  infoText: {
    fontSize: 13,
    color: COLORS.textSecondary,
    lineHeight: 18,
  },

  // Action Buttons Section
  actionButtonsGroup: {
    gap: SPACING.md,
    marginBottom: SPACING.xl,
  },
  btnPrimary: {
    backgroundColor: COLORS.primaryOrange,
    paddingVertical: SPACING.lg,
    borderRadius: RADIUS.lg,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: COLORS.primaryOrange,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 5,
  },
  btnPrimaryText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
    letterSpacing: 0.3,
  },

  btnSecondary: {
    backgroundColor: COLORS.crimsonRed,
    paddingVertical: SPACING.lg,
    borderRadius: RADIUS.lg,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: COLORS.crimsonRed,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
    elevation: 5,
  },
  btnSecondaryText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
    letterSpacing: 0.3,
  },

  btnDisabled: {
    backgroundColor: COLORS.disabledBg,
    borderColor: COLORS.cardBorder,
    borderWidth: 1,
    shadowOpacity: 0,
    elevation: 0,
  },
  btnDisabledText: {
    color: COLORS.disabledText,
  },
  disabledHintText: {
    fontSize: 12,
    color: COLORS.crimsonRed,
    textAlign: "center",
    marginTop: 4,
    fontWeight: "500",
  },

  // Weekly Trends Card
  trendHeaderRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: SPACING.md,
  },
  trendStatRow: {
    flexDirection: "row",
    alignItems: "baseline",
    gap: SPACING.xs,
    marginBottom: SPACING.xs,
  },
  trendStatNumber: {
    fontSize: 32,
    fontWeight: "800",
    color: COLORS.textPrimary,
  },
  trendStatUnit: {
    fontSize: 14,
    fontWeight: "600",
    color: COLORS.textSecondary,
  },
  trendNoteText: {
    fontSize: 14,
    fontWeight: "500",
    color: COLORS.successGreen,
  },
  emptyStateText: {
    fontSize: 14,
    color: COLORS.textMuted,
    fontStyle: "italic",
  },

  // View Workouts Entry Card
  workoutNavCard: {
    backgroundColor: COLORS.cardBg,
    borderRadius: RADIUS.lg,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    padding: SPACING.lg,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: SPACING.xl,
  },
  workoutNavTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: COLORS.textPrimary,
  },
  workoutNavSubtext: {
    fontSize: 12,
    color: COLORS.textSecondary,
    marginTop: 2,
  },
  chevronIcon: {
    fontSize: 20,
    color: COLORS.primaryOrange,
    fontWeight: "700",
  },

  // Biomechanics Modules Grid
  modulesHeading: {
    fontSize: 18,
    fontWeight: "700",
    color: COLORS.textPrimary,
    marginBottom: SPACING.md,
  },
  modulesGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: SPACING.md,
  },
  moduleCard: {
    width: "47%",
    backgroundColor: COLORS.cardBg,
    borderRadius: RADIUS.md,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    padding: SPACING.md,
  },
  moduleBadge: {
    alignSelf: "flex-start",
    paddingHorizontal: SPACING.sm,
    paddingVertical: 2,
    borderRadius: RADIUS.sm,
    marginBottom: SPACING.sm,
  },
  moduleBadgeText: {
    fontSize: 10,
    fontWeight: "800",
  },
  moduleTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: COLORS.textPrimary,
    marginBottom: 4,
  },
  moduleDescription: {
    fontSize: 11,
    color: COLORS.textSecondary,
    lineHeight: 15,
  },
  // Physical Information Editing
  editHint: {
    fontSize: 11,
    color: COLORS.textMuted,
    textAlign: "center",
    marginTop: -SPACING.xs,
  },

  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.75)",
    justifyContent: "center",
    paddingHorizontal: SPACING.lg,
  },
  modalKeyboardContainer: {
    flex: 1,
    justifyContent: "center",
  },
  modalCard: {
    backgroundColor: COLORS.cardBg,
    borderRadius: RADIUS.lg,
    borderWidth: 1,
    borderColor: COLORS.cardBorder,
    padding: SPACING.xl,
  },
  modalTitle: {
    color: COLORS.textPrimary,
    fontSize: 20,
    fontWeight: "700",
    marginBottom: SPACING.xs,
  },
  modalSubtitle: {
    color: COLORS.textSecondary,
    fontSize: 13,
    lineHeight: 19,
    marginBottom: SPACING.xl,
  },
  modalInput: {
    marginTop: SPACING.xs,
    marginBottom: SPACING.lg,
  },
  modalError: {
    color: COLORS.crimsonRed,
    fontSize: 12,
    lineHeight: 18,
    marginBottom: SPACING.md,
  },
  modalActions: {
    flexDirection: "row",
    gap: SPACING.md,
    marginTop: SPACING.sm,
  },
  modalButton: {
    flex: 1,
    paddingVertical: SPACING.md,
    paddingHorizontal: SPACING.sm,
    borderRadius: RADIUS.md,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 46,
  },
  modalPrimaryButton: {
    backgroundColor: COLORS.primaryOrange,
  },
  modalSecondaryButton: {
    backgroundColor: COLORS.inputBg,
    borderWidth: 1,
    borderColor: COLORS.inputBorder,
  },
  modalButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "700",
  },
  modalSecondaryButtonText: {
    color: COLORS.textPrimary,
    fontSize: 14,
    fontWeight: "600",
  },
});

export default styles;
("");
