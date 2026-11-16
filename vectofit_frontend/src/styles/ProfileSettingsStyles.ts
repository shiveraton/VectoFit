import { StyleSheet } from "react-native";
import { COLORS, SPACING } from "./designTokens";

export default StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: COLORS.bgDark },
  content: { padding: SPACING.lg, paddingBottom: SPACING.xxxl, gap: SPACING.xxl },
  section: { gap: SPACING.sm },
  heading: { fontSize: 18, lineHeight: 26, color: COLORS.textPrimary },
  body: { fontSize: 16, lineHeight: 24, color: COLORS.textSecondary },
  field: { gap: SPACING.sm },
  label: { fontSize: 16, color: COLORS.textPrimary },
  input: {
    minHeight: 48,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.md,
    borderWidth: 1,
    borderRadius: 8,
    borderColor: COLORS.textMuted,
    backgroundColor: COLORS.cardBg,
    color: COLORS.textPrimary,
    fontSize: 16,
  },
  button: {
    minHeight: 48,
    padding: SPACING.md,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: COLORS.primaryOrange,
  },
  buttonText: { fontSize: 16, color: COLORS.bgDark },
  disabled: { opacity: 0.5 },
  error: { fontSize: 14, lineHeight: 22, color: COLORS.crimsonRed },
});
