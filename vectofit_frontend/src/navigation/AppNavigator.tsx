import { RootStackParamList } from "./types";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { MainTabNavigator } from "../screens/MainTabNavigator";
import useAuthStore from "../stores/useAuthStore";

import LoginScreen from "../screens/LoginScreen";
import RegisterScreen from "../screens/RegisterScreen";
import MorphologicalCalibrationScreen from "../screens/MorphologicalCalibrationScreen";
import CameraPoseScreen from "../screens/CameraPoseScreen";

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
