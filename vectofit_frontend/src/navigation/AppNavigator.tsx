import type { RootStackParamList } from "./types";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { MainTabNavigator } from "../screens/MainTabNavigator";
import useAuthStore from "../stores/useAuthStore";

import LoginScreen from "../screens/LoginScreen";
import RegisterScreen from "../screens/RegisterScreen";
import MorphologicalCalibrationScreen from "../screens/MorphologicalCalibrationScreen";
import CameraPoseScreen from "../screens/CameraPoseScreen";

import EditProfileScreen from "../screens/EditProfileScreen";
import NotificationsScreen from "../screens/NotificationsScreen";
import PrivacySecurityScreen from "../screens/PrivacySecurityScreen";
import HelpSupportScreen from "../screens/HelpSupportScreen";
import { COLORS } from "../styles/designTokens";

const Stack = createNativeStackNavigator<RootStackParamList>();

export const AppNavigator = () => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName={isAuthenticated ? "MainTabs" : "Login"}
        screenOptions={{
          headerShown: true,
          headerStyle: { backgroundColor: "#0f172a" },
          headerTintColor: "#fff",
          contentStyle: { backgroundColor: "#020617" },
        }}
      >
        {isAuthenticated ? (
          <>
            <Stack.Screen
              name="MainTabs"
              component={MainTabNavigator}
              options={{ headerShown: false }}
            />
            <Stack.Group screenOptions={{ headerStyle: { backgroundColor: COLORS.cardBg }, headerTintColor: COLORS.textPrimary, contentStyle: { backgroundColor: COLORS.bgDark } }}>
              <Stack.Screen name="EditProfile" component={EditProfileScreen} options={{ title: "Edit Profile" }} />
              <Stack.Screen name="Notifications" component={NotificationsScreen} options={{ title: "Notifications" }} />
              <Stack.Screen name="PrivacySecurity" component={PrivacySecurityScreen} options={{ title: "Privacy & Security" }} />
              <Stack.Screen name="HelpSupport" component={HelpSupportScreen} options={{ title: "Help & Support" }} />
            </Stack.Group>
            <Stack.Screen
              name="MorphologicalCalibration"
              component={MorphologicalCalibrationScreen}
              options={{
                headerShown: false,
              }}
            />
            <Stack.Screen
              name="CameraPose"
              component={CameraPoseScreen}
              options={{
                headerShown: false,
              }}
            />
          </>
        ) : (
          <>
            <Stack.Screen name="Login" component={LoginScreen} />
            <Stack.Screen name="Register" component={RegisterScreen} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
};
