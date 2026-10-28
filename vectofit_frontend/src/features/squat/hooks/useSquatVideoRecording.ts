import { useCallback, useRef, useState } from "react";
import { useVideoOutput } from "react-native-vision-camera";
import type { Recorder } from "react-native-vision-camera";

type VideoOutput = ReturnType<typeof useVideoOutput>;

export function useSquatVideoRecording(videoOutput: VideoOutput) {
  const recorderRef = useRef<Recorder | null>(null);
  const finishedPromiseRef = useRef<Promise<string | null> | null>(null);
  const resolveFinishedRef = useRef<((path: string | null) => void) | null>(
    null,
  );

  const [isRecording, setIsRecording] = useState(false);
  const [recordedVideoPath, setRecordedVideoPath] = useState<string | null>(
    null,
  );
  const [recordingError, setRecordingError] = useState<string | null>(null);

  const startRecording = useCallback(async (): Promise<boolean> => {
    if (recorderRef.current) return false;

    setRecordingError(null);
    setRecordedVideoPath(null);

    try {
      const recorder = await videoOutput.createRecorder({});
      recorderRef.current = recorder;

      const finishedPromise = new Promise<string | null>((resolve) => {
        resolveFinishedRef.current = resolve;
      });

      finishedPromiseRef.current = finishedPromise;

      await recorder.startRecording(
        (filePath, _reason) => {
          setRecordedVideoPath(filePath);
          setIsRecording(false);

          if (recorderRef.current === recorder) {
            recorderRef.current = null;
          }

          const resolve = resolveFinishedRef.current;
          resolveFinishedRef.current = null;
          finishedPromiseRef.current = null;
          resolve?.(filePath);
        },
        (error) => {
          setRecordingError(error.message);
          setIsRecording(false);

          if (recorderRef.current === recorder) {
            recorderRef.current = null;
          }

          const resolve = resolveFinishedRef.current;
          resolveFinishedRef.current = null;
          finishedPromiseRef.current = null;
          resolve?.(null);
        },
      );

      if (recorderRef.current !== recorder) {
        return false;
      }

      setIsRecording(true);
      return true;
    } catch (error) {
      setRecordingError(error instanceof Error ? error.message : String(error));

      recorderRef.current = null;
      resolveFinishedRef.current?.(null);
      resolveFinishedRef.current = null;
      finishedPromiseRef.current = null;
      setIsRecording(false);

      return false;
    }
  }, [videoOutput]);

  const stopRecording = useCallback(async (): Promise<string | null> => {
    const recorder = recorderRef.current;

    if (!recorder) return recordedVideoPath;

    const finishedPromise = finishedPromiseRef.current;

    try {
      await recorder.stopRecording();

      return finishedPromise ? await finishedPromise : null;
    } catch (error) {
      setRecordingError(error instanceof Error ? error.message : String(error));
      return null;
    } finally {
      if (recorderRef.current === recorder) {
        recorderRef.current = null;
      }
      setIsRecording(false);
    }
  }, [recordedVideoPath]);

  const clearRecording = useCallback(() => {
    if (recorderRef.current) return;

    setRecordedVideoPath(null);
    setRecordingError(null);
  }, []);

  return {
    startRecording,
    stopRecording,
    clearRecording,
    isRecording,
    recordedVideoPath,
    recordingError,
  };
}
