import { NitroModules } from "react-native-nitro-modules";
import type { PoseLandmarkerPlugin } from "../native/PoseLandmarkerPlugin.nitro";

export const poseLandmarkerPlugin =
  NitroModules.createHybridObject<PoseLandmarkerPlugin>("PoseLandmarkerPlugin");
