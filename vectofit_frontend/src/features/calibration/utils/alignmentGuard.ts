export interface Landmark {
  id: number;
  x_coordinate: number;
  y_coordinate: number;
  z_coordinate: number;
  visibility: number;
}

const CRITICAL_LANDMARKS = [0, 11, 12, 23, 24, 27, 28];
const VISIBILITY_THRESHOLD = 0.85;

export const validateCalibrationPose = (
  landmarks: Landmark[],
): { isValid: boolean; reason?: string } => {
  if (!landmarks || landmarks.length === 0) {
    return { isValid: false, reason: "No pose detected" };
  }

  const missingPoints = CRITICAL_LANDMARKS.filter(
    (id) => !landmarks[id] || landmarks[id].visibility < VISIBILITY_THRESHOLD,
  );

  if (missingPoints.length > 0) {
    return {
      isValid: false,
      reason: "Step back to show your full body from head to ankles",
    };
  }

  const leftShoulder = landmarks[11];
  const rightShoulder = landmarks[12];
  const shoulderTilt = Math.abs(
    leftShoulder.y_coordinate - rightShoulder.y_coordinate,
  );

  if (shoulderTilt > 0.05) {
    return {
      isValid: false,
      reason: "Level your shoulders and stand straight",
    };
  }

  return { isValid: true };
};
