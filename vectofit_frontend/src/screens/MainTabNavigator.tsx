import React from "react";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import Ionicons from "react-native-vector-icons/Ionicons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { RootStackParamList } from "../navigation/types";
import HomeScreen from "./HomeScreen";
import InsightsNavigator from "../navigation/InsightsNavigator";
import ProfileScreen from "./ProfileScreen";
import { COLORS } from "../styles/designTokens";

const Tab = createBottomTabNavigator<RootStackParamList>();

export const MainTabNavigator = () => {
  const insets = useSafeAreaInsets();

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: string;

          switch (route.name) {
            case "Home":
              iconName = focused ? "grid" : "grid-outline";
              break;
            case "Insights":
              iconName = focused ? "analytics" : "analytics-outline";
              break;
            case "Profile":
              iconName = focused ? "person" : "person-outline";
              break;
            default:
              iconName = "square";
          }

          return <Ionicons name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: COLORS.primaryOrange,
        tabBarInactiveTintColor: COLORS.textMuted,
        headerShown: false,
        sceneStyle: { backgroundColor: COLORS.bgDark },
        tabBarStyle: {
          backgroundColor: COLORS.cardBg,
          borderTopColor: COLORS.cardBorder,
          borderTopWidth: 1,
          height: 60 + insets.bottom,
          paddingBottom: insets.bottom > 0 ? insets.bottom : 8,
          paddingTop: 8,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: "600",
          letterSpacing: 0.3,
        },
      })}
    >
      <Tab.Screen
        name="Home"
        component={HomeScreen}
        options={{ title: "Dashboard" }}
      />
      <Tab.Screen
        name="Insights"
        component={InsightsNavigator}
        options={{ title: "Insights" }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{ title: "Profile" }}
      />
    </Tab.Navigator>
  );
};
