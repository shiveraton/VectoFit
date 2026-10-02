import { StyleSheet } from "react-native";
import { COLORS, SPACING, RADIUS } from "./HomeScreenStyles";

export const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.bgDark,
    padding: SPACING.xl,
    justifyContent: "center",
  },
  title: {
    fontFamily: "SegoeUI-Bold",
    fontSize: 32,
    color: COLORS.textPrimary,
    marginBottom: SPACING.xxxl,
    textAlign: "center",
  },
  label: {
    fontSize: 14,
    fontWeight: "600",
    color: COLORS.textSecondary,
    marginBottom: SPACING.sm,
    textTransform: "uppercase",
  },
  input: {
    backgroundColor: COLORS.inputBg,
    borderWidth: 1,
    borderColor: COLORS.inputBorder,
    borderRadius: RADIUS.md,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.md,
    fontSize: 16,
    color: COLORS.textPrimary,
    marginBottom: SPACING.lg,
  },
  button: {
    backgroundColor: COLORS.primaryOrange,
    paddingVertical: SPACING.lg,
    borderRadius: RADIUS.lg,
    alignItems: "center",
    marginTop: SPACING.md,
  },
  buttonDisabled: {
    backgroundColor: COLORS.disabledBg,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },
  linkButton: {
    marginTop: SPACING.xl,
    alignItems: "center",
  },
  linkText: {
    color: COLORS.primaryOrange,
    fontSize: 14,
    fontWeight: "600",
  },
});
