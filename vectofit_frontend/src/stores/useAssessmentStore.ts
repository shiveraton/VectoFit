import { create } from "zustand";

interface AssessmentState {
  calibration: {
    scaleFactor: number | null;
    segmentLengths: Record<string, number> | null;
    isCalibrated: boolean;
  };
  setCalibration: (
    scaleFactor: number,
    segmentLengths: Record<string, number>,
  ) => void;
}

export const useAssessmentStore = create<AssessmentState>((set) => ({
  calibration: { scaleFactor: null, segmentLengths: null, isCalibrated: false },
  setCalibration: (scaleFactor, segmentLengths) =>
    set({ calibration: { scaleFactor, segmentLengths, isCalibrated: true } }),
}));
