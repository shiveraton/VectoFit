import { useCallback, useEffect, useRef, useState } from "react";
import { AppState } from "react-native";
import { useIsFocused } from "@react-navigation/native";
import { requireOptionalNativeModule } from "expo";
import type { useCameraPoseScreen } from "./useCameraPoseScreen";
import { getKneeAlignmentCue, parseVoiceCommand } from "../services/kneeAlignmentCue";

interface VoiceOptions {
  camera: ReturnType<typeof useCameraPoseScreen>;
  canStart: boolean;
}

interface VoiceModules {
  recognition: typeof import("expo-speech-recognition").ExpoSpeechRecognitionModule;
  speech: typeof import("expo-speech");
}

const CUE_PERSISTENCE_MS = 600;
const CUE_COOLDOWN_MS = 8000;

export function useSquatVoice(options: VoiceOptions) {
  const [enabled, setEnabled] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isRequestingPermission, setIsRequestingPermission] = useState(false);
  const [needsSettings, setNeedsSettings] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cueMessage, setCueMessage] = useState<string | null>(null);
  const [foreground, setForeground] = useState(AppState.currentState === "active");
  const isFocused = useIsFocused();
  const latest = useRef(options);
  latest.current = options;
  const mounted = useRef(true);
  const permissionPending = useRef(false);
  const commandPending = useRef(false);
  const speaking = useRef(false);
  const utteranceId = useRef(0);
  const speechTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const candidate = useRef({ key: "", since: 0, lastSeen: 0 });
  const lastSpokenAt = useRef(0);
  const modules = useRef<VoiceModules | null>(null);

  const stopSpeaking = useCallback(() => {
    utteranceId.current++;
    if (speechTimer.current) clearTimeout(speechTimer.current);
    speechTimer.current = null;
    if (speaking.current) void modules.current?.speech.stop().catch(() => {});
    speaking.current = false;
    if (mounted.current) setIsSpeaking(false);
  }, []);

  useEffect(() => {
    mounted.current = true;
    const subscription = AppState.addEventListener("change", (state) => {
      setForeground(state === "active");
    });
    return () => {
      mounted.current = false;
      subscription.remove();
      stopSpeaking();
    };
  }, [stopSpeaking]);

  const toggle = useCallback(async () => {
    if (permissionPending.current) return;
    if (enabled) {
      setEnabled(false);
      return;
    }
    permissionPending.current = true;
    setIsRequestingPermission(true);
    setError(null);
    setNeedsSettings(false);
    try {
      const Recognition = requireOptionalNativeModule<VoiceModules["recognition"]>("ExpoSpeechRecognition");
      if (!Recognition || !requireOptionalNativeModule("ExpoSpeech")) {
        setError("Voice requires the updated app. Install the latest Android build, then reopen VectoFit.");
        return;
      }
      modules.current = { recognition: Recognition, speech: require("expo-speech") };
      if (!Recognition.isRecognitionAvailable()) {
        setError("Speech recognition is unavailable. Enable a speech recognition service on your device.");
        return;
      }
      const permission = await Recognition.requestPermissionsAsync();
      if (!mounted.current) return;
      if (!permission.granted) {
        setNeedsSettings(!permission.canAskAgain);
        setError("Allow microphone and speech recognition access to use voice mode.");
        return;
      }
      setEnabled(true);
    } catch {
      if (mounted.current) setError("Voice mode could not start. Tap Voice to try again.");
    } finally {
      permissionPending.current = false;
      if (mounted.current) setIsRequestingPermission(false);
    }
  }, [enabled]);

  const busy = options.camera.isStartingSession || options.camera.isUploadingAssessment;
  const voiceActive = enabled && isFocused && foreground && options.camera.isCameraActive && !busy;

  useEffect(() => {
    const Recognition = modules.current?.recognition;
    if (!voiceActive || !Recognition) {
      setIsListening(false);
      return;
    }
    let disposed = false;
    let checkingState = false;
    let restartTimer: ReturnType<typeof setTimeout> | undefined;

    const fail = (message: string) => {
      if (disposed) return;
      setError(message);
      setEnabled(false);
    };

    const startListening = async () => {
      if (disposed || checkingState) return;
      checkingState = true;
      try {
        const state = await Recognition.getStateAsync();
        if (disposed) return;
        if (state !== "inactive") {
          restartTimer = setTimeout(() => void startListening(), 500);
          return;
        }
        Recognition.start({
          lang: "en-US",
          interimResults: false,
          continuous: false,
          maxAlternatives: 1,
          contextualStrings: ["Start", "Stop"],
          iosTaskHint: "confirmation",
          iosVoiceProcessingEnabled: true,
        });
      } catch {
        fail("Voice recognition stopped. Tap Voice to reconnect.");
      } finally {
        checkingState = false;
      }
    };

    const subscriptions = [
      Recognition.addListener("start", () => {
        if (!disposed) setIsListening(true);
      }),
      Recognition.addListener("end", () => {
        if (disposed) return;
        setIsListening(false);
        clearTimeout(restartTimer);
        restartTimer = setTimeout(() => void startListening(), 500);
      }),
      Recognition.addListener("error", (event) => {
        if (disposed || event.error === "aborted" || event.error === "no-speech" ||
          event.error === "speech-timeout") return;
        fail("Voice recognition is unavailable. Tap Voice to retry or use the session button.");
      }),
      Recognition.addListener("result", async (event) => {
        if (disposed || AppState.currentState !== "active" || !event.isFinal || commandPending.current) return;
        const command = parseVoiceCommand(event.results[0]?.transcript ?? "");
        const current = latest.current;
        if (command === "start" && !current.canStart) return;
        if (command === "stop" && !current.camera.isSessionActive) return;
        if (!command) return;
        commandPending.current = true;
        try {
          if (command === "start") await current.camera.startSession();
          else {
            stopSpeaking();
            await current.camera.stopSession();
          }
        } catch {
          if (!disposed) setError("The voice command could not finish. Use the session button to retry.");
        } finally {
          commandPending.current = false;
        }
      }),
    ];
    void startListening();
    return () => {
      disposed = true;
      clearTimeout(restartTimer);
      subscriptions.forEach((subscription) => subscription.remove());
      try {
        Recognition.abort();
      } catch {}
    };
  }, [voiceActive, stopSpeaking]);

  const { camera } = options;
  useEffect(() => {
    const Speech = modules.current?.speech;
    if (!Speech) return;
    const now = Date.now();
    const cue = voiceActive && camera.isSessionActive && camera.pose.bodyVisible
      ? getKneeAlignmentCue(camera.pose.landmarks, camera.pose.frameWidth, camera.pose.frameHeight)
      : null;
    if (!cue) {
      candidate.current = { key: "", since: 0, lastSeen: 0 };
      if (!voiceActive || !camera.isSessionActive) lastSpokenAt.current = 0;
      setCueMessage(null);
      if (!voiceActive || !camera.isSessionActive || !camera.pose.bodyVisible) stopSpeaking();
      return;
    }
    if (candidate.current.key !== cue.key || now - candidate.current.lastSeen > 350) {
      candidate.current = { key: cue.key, since: now, lastSeen: now };
      setCueMessage(null);
    }
    candidate.current.lastSeen = now;
    if (now - candidate.current.since < CUE_PERSISTENCE_MS) return;
    setCueMessage(cue.message);
    if (speaking.current || now - lastSpokenAt.current < CUE_COOLDOWN_MS) return;

    lastSpokenAt.current = now;
    speaking.current = true;
    setIsSpeaking(true);
    const id = ++utteranceId.current;
    const finish = () => {
      if (!mounted.current || utteranceId.current !== id) return;
      if (speechTimer.current) clearTimeout(speechTimer.current);
      speechTimer.current = null;
      speaking.current = false;
      setIsSpeaking(false);
    };
    const playbackFailed = () => {
      if (!mounted.current || utteranceId.current !== id) return;
      stopSpeaking();
      setError("Voice playback failed. Tap Voice to try again.");
      setEnabled(false);
    };
    speechTimer.current = setTimeout(playbackFailed, 15000);
    try {
      Speech.speak(cue.message, {
        language: "en-US",
        rate: 0.95,
        useApplicationAudioSession: true,
        onDone: finish,
        onStopped: finish,
        onError: playbackFailed,
      });
    } catch {
      playbackFailed();
    }
  }, [camera.pose, camera.isSessionActive, voiceActive, stopSpeaking]);

  return {
    enabled,
    isListening,
    isSpeaking,
    isRequestingPermission,
    needsSettings,
    error,
    cueMessage,
    toggle,
  };
}
