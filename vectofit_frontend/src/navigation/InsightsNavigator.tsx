import React from "react";
import { createNativeStackNavigator } from "@react-navigation/native-stack";

import type { InsightsStackParamList } from "./insightsTypes";
import InsightsScreen from "../screens/InsightsScreen";
import SessionResultScreen from "../screens/SessionResultScreen";
import { COLORS } from "../styles/designTokens";

const Stack = createNativeStackNavigator<InsightsStackParamList>();

export default function InsightsNavigator() {
  return (
    <Stack.Navigator
      initialRouteName="SessionHistory"
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: COLORS.bgDark },
        animation: "slide_from_right",
      }}
    >
      <Stack.Screen name="SessionHistory" component={InsightsScreen} />
      <Stack.Screen name="SessionResult" component={SessionResultScreen} />
    </Stack.Navigator>
  );
}
