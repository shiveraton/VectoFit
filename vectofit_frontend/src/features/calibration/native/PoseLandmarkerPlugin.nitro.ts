import type { HybridObject } from "react-native-nitro-modules";
import type { Frame } from "react-native-vision-camera";

export interface PoseLandmarkerPlugin extends HybridObject<{
  android: "kotlin";
  ios: "swift";
}> {
  detect(frame: Frame): number[];
}
