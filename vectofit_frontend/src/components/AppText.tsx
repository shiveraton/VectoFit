import React from "react";
import { Text as RNText, TextProps, StyleSheet } from "react-native";
import { FONTS } from "../theme/fonts";
import { COLORS } from "../theme/colors";

interface AppTextProps extends TextProps {
  variant?: "regular" | "semiBold" | "bold";
}

export const AppText: React.FC<AppTextProps> = ({
  style,
  variant = "regular",
  children,
  ...props
}) => {
  const getFontFamily = () => {
    switch (variant) {
      case "bold":
        return FONTS.bold;
      case "semiBold":
        return FONTS.semiBold;
      default:
        return FONTS.regular;
    }
  };

  return (
    <RNText
      style={[
        { fontFamily: getFontFamily(), color: COLORS.textPrimary },
        style,
      ]}
      {...props}
    >
      {children}
    </RNText>
  );
};
