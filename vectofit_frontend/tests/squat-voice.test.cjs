const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");
const ts = require("typescript");

function load(relativePath, imports = {}, globals = {}) {
  const filename = path.join(__dirname, "../src/features/squat", relativePath);
  const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText;
  const context = {
    exports: {}, ...globals,
    require(name) {
      globals.onRequire?.(name);
      if (name === globals.missingNativeModule) {
        throw new Error(`Cannot find native module '${name}'`);
      }
      assert.ok(name in imports, `Unexpected import ${name}`);
      return imports[name];
    },
  };
  vm.runInNewContext(compiled, context, { filename });
  return context.exports;
}

const alignment = load("services/kneeAlignmentCue.ts");

function pose(leftOffset = 0, rightOffset = 0) {
  const landmarks = Array.from({ length: 33 }, (_, id) => ({
    id, x_coordinate: 0.5, y_coordinate: 0.5, visibility: 1,
  }));
  for (const [hip, knee, ankle, x, offset] of [
    [23, 25, 27, 0.35, leftOffset], [24, 26, 28, 0.65, rightOffset],
  ]) {
    landmarks[hip].x_coordinate = x;
    landmarks[hip].y_coordinate = 0.3;
    landmarks[knee].x_coordinate = x + offset;
    landmarks[knee].y_coordinate = 0.55;
    landmarks[ankle].x_coordinate = x;
    landmarks[ankle].y_coordinate = 0.8;
  }
  return { landmarks, bodyVisible: true, frameWidth: 720, frameHeight: 1280 };
}

function cue(value) {
  return alignment.getKneeAlignmentCue(value.landmarks, value.frameWidth, value.frameHeight);
}

test("only exact session commands are accepted, including punctuation and capitalization", () => {
  assert.equal(alignment.parseVoiceCommand(" Start! "), "start");
  assert.equal(alignment.parseVoiceCommand("STOP SESSION."), "stop");
  for (const text of ["do not start", "start stop", "your knees are caving in", "restart", "stopped"]) {
    assert.equal(alignment.parseVoiceCommand(text), null);
  }
});

test("signed FPPA distinguishes left, right, bilateral inward and outward cues", () => {
  assert.equal(cue(pose()), null);
  assert.equal(cue(pose(0.08)).key, "left-inward");
  assert.equal(cue(pose(0, -0.08)).key, "right-inward");
  assert.equal(cue(pose(0.08, -0.08)).key, "both-inward");
  assert.match(cue(pose(0.08, -0.08)).message, /knees are caving in/);
  assert.equal(cue(pose(-0.08)).key, "left-outward");
  assert.equal(cue(pose(0, 0.08)).key, "right-outward");
  assert.match(cue(pose(-0.08, 0.08)).message, /knees are drifting out/);
});

test("mirror transforms preserve anatomical direction and pixel scaling controls the angle", () => {
  const original = pose(0.08);
  const mirrored = { ...original, landmarks: original.landmarks.map((point) => ({
    ...point, x_coordinate: 1 - point.x_coordinate,
  })) };
  assert.equal(cue(mirrored).key, cue(original).key);
  assert.equal(cue({ ...original, frameWidth: 100 }), null);
});

test("missing, low-visibility, nonfinite and degenerate evidence cannot produce a cue", () => {
  for (const mutate of [
    (value) => { value.landmarks[25].visibility = 0.49; },
    (value) => { value.landmarks[24].x_coordinate = NaN; },
    (value) => { value.landmarks[25] = { ...value.landmarks[23] }; },
    (value) => { value.frameWidth = 0; },
    (value) => { value.landmarks = []; },
  ]) {
    const value = pose(0.08);
    mutate(value);
    assert.equal(cue(value), null);
  }
});

test("live cutoff matches the backend's predeclared FPPA cutoff", () => {
  const backend = fs.readFileSync(path.join(__dirname, "../../vectofit_backend/apps/analytics/services/fppa.py"), "utf8");
  assert.match(backend, /FPPA_CUTOFF_DEG = 10\.0/);
  const below = Math.tan(4 * Math.PI / 180) * 0.25 * 1280 / 720;
  const above = Math.tan(6 * Math.PI / 180) * 0.25 * 1280 / 720;
  assert.equal(cue(pose(below)), null);
  assert.equal(cue(pose(above)).key, "left-inward");
});

function voiceHarness(missingNativeModule) {
  const slots = [];
  let cursor = 0;
  let dirty = false;
  let effects = [];
  let time = 10000;
  let nextTimer = 0;
  const timers = new Map();
  const listeners = new Map();
  let recognitionState = "inactive";
  let focused = true;
  let permission = { granted: true, canAskAgain: true };
  let appStateListener;
  let starts = 0;
  let stops = 0;
  let speechStops = 0;
  let activeSpeech;
  let unavailableModuleLoads = 0;
  const spoken = [];
  const appState = { currentState: "active", addEventListener(name, listener) {
    appStateListener = listener;
    return { remove() {} };
  } };
  const options = {
    canStart: true,
    camera: {
      isCameraActive: true, isStartingSession: false, isUploadingAssessment: false,
      isSessionActive: false, pose: pose(),
      async startSession() { starts++; },
      async stopSession() { stops++; return "/video.mp4"; },
    },
  };
  function changed(before, after) {
    return !before || before.length !== after.length || before.some((item, index) => !Object.is(item, after[index]));
  }
  const react = {
    useState(initial) {
      const index = cursor++;
      if (!slots[index]) slots[index] = { value: initial };
      return [slots[index].value, (value) => {
        const next = typeof value === "function" ? value(slots[index].value) : value;
        if (!Object.is(next, slots[index].value)) { slots[index].value = next; dirty = true; }
      }];
    },
    useRef(initial) {
      const index = cursor++;
      if (!slots[index]) slots[index] = { current: initial };
      return slots[index];
    },
    useCallback(callback, deps) {
      const index = cursor++;
      if (!slots[index] || changed(slots[index].deps, deps)) slots[index] = { value: callback, deps };
      return slots[index].value;
    },
    useEffect(effect, deps) {
      const index = cursor++;
      if (!slots[index] || changed(slots[index].deps, deps)) {
        const previous = slots[index];
        slots[index] = { deps };
        effects.push(() => { previous?.cleanup?.(); slots[index].cleanup = effect(); });
      }
    },
  };
  function emit(name, value) {
    return Promise.all([...(listeners.get(name) ?? [])].map((listener) => listener(value)));
  }
  const recognition = {
    isRecognitionAvailable: () => true,
    requestPermissionsAsync: async () => permission,
    getStateAsync: async () => recognitionState,
    start() { recognitionState = "recognizing"; void emit("start"); },
    abort() { recognitionState = "inactive"; void emit("end"); },
    addListener(name, callback) {
      if (!listeners.has(name)) listeners.set(name, new Set());
      listeners.get(name).add(callback);
      return { remove: () => listeners.get(name).delete(callback) };
    },
  };
  const module = load("hooks/useSquatVoice.ts", {
    react,
    "react-native": { AppState: appState },
    "@react-navigation/native": { useIsFocused: () => focused },
    expo: { requireOptionalNativeModule(name) {
      if (name === "ExpoSpeechRecognition") {
        return missingNativeModule === "expo-speech-recognition" ? null : recognition;
      }
      return missingNativeModule === "expo-speech" ? null : {};
    } },
    "expo-speech": {
      speak(message, callbacks) { spoken.push(message); activeSpeech = callbacks; },
      async stop() { speechStops++; activeSpeech?.onStopped(); activeSpeech = null; },
    },
    "../services/kneeAlignmentCue": alignment,
  }, {
    missingNativeModule,
    onRequire: (name) => { if (name === missingNativeModule) unavailableModuleLoads++; },
    Date: { now: () => time },
    setTimeout(callback, delay) { const id = ++nextTimer; timers.set(id, { callback, at: time + delay }); return id; },
    clearTimeout: (id) => timers.delete(id),
  });
  let result;
  function render() {
    for (let round = 0; round < 20; round++) {
      dirty = false;
      cursor = 0;
      result = module.useSquatVoice(options);
      const pending = effects;
      effects = [];
      pending.forEach((effect) => effect());
      if (!dirty) return result;
    }
    throw new Error("Hook did not settle");
  }
  async function settle() {
    for (let round = 0; round < 4; round++) { await Promise.resolve(); render(); }
  }
  return {
    options, spoken, render, settle,
    async enable() { await render().toggle(); render(); await settle(); },
    async command(text, isFinal = true) {
      await emit("result", { isFinal, results: [{ transcript: text }] });
      await settle();
    },
    advance(milliseconds) {
      time += milliseconds;
      for (const [id, timer] of [...timers]) {
        if (timer.at <= time) { timers.delete(id); timer.callback(); }
      }
      render();
    },
    frame(value) { options.camera.pose = value; render(); },
    denyPermission() { permission = { granted: false, canAskAgain: false }; },
    background() { appState.currentState = "background"; appStateListener("background"); render(); },
    blur() { focused = false; render(); },
    endSpeech() { activeSpeech?.onDone(); activeSpeech = null; render(); },
    unmount() { slots.forEach((slot) => slot?.cleanup?.()); },
    counts: () => ({ starts, stops, speechStops, unavailableModuleLoads, listeners: [...listeners.values()].reduce((sum, set) => sum + set.size, 0) }),
  };
}

for (const missingModule of ["expo-speech-recognition", "expo-speech"]) {
  test(`missing ${missingModule} keeps capture usable and explains the required app update`, async () => {
    const voice = voiceHarness(missingModule);
    assert.doesNotThrow(() => voice.render());
    await voice.enable();
    assert.equal(voice.render().enabled, false);
    assert.match(voice.render().error, /Install the latest Android build/);
    assert.equal(voice.counts().listeners, 0);
    assert.equal(voice.counts().starts, 0);
    assert.equal(voice.counts().unavailableModuleLoads, 0);
  });
}

test("voice permission denial stays off and exposes Settings recovery", async () => {
  const voice = voiceHarness();
  voice.denyPermission();
  await voice.enable();
  assert.equal(voice.render().enabled, false);
  assert.equal(voice.render().needsSettings, true);
  assert.equal(voice.counts().listeners, 0);
});

test("commands use current readiness and session state and ignore interim or coaching text", async () => {
  const voice = voiceHarness();
  await voice.enable();
  assert.equal(voice.render().isListening, true);
  await voice.command("start", false);
  await voice.command("Your knees are caving in. Keep both knees tracking over your feet.");
  voice.options.canStart = false;
  voice.render();
  await voice.command("start");
  await voice.command("stop");
  assert.equal(voice.counts().starts, 0);
  assert.equal(voice.counts().stops, 0);
  voice.options.canStart = true;
  voice.render();
  await voice.command("Start!");
  voice.options.camera.isSessionActive = true;
  voice.render();
  await voice.command("Stop.");
  assert.equal(voice.counts().starts, 1);
  assert.equal(voice.counts().stops, 1);
});

test("cues require persistent visible evidence, never queue, and respect cooldown", async () => {
  const voice = voiceHarness();
  await voice.enable();
  voice.options.camera.isSessionActive = true;
  for (let frame = 0; frame < 7; frame++) {
    voice.frame(pose(0.08, -0.08));
    voice.advance(100);
  }
  assert.equal(voice.spoken.length, 1);
  assert.match(voice.spoken[0], /knees are caving in/);
  voice.frame(pose());
  assert.equal(voice.render().isSpeaking, true);
  voice.endSpeech();
  for (let frame = 0; frame < 10; frame++) {
    voice.frame(pose(0.08, -0.08));
    voice.advance(100);
  }
  assert.equal(voice.spoken.length, 1);
  voice.frame({ ...pose(), bodyVisible: false });
  assert.equal(voice.render().cueMessage, null);
  voice.advance(8000);
  for (let frame = 0; frame < 7; frame++) {
    voice.frame(pose(-0.08, 0.08));
    voice.advance(100);
  }
  assert.equal(voice.spoken.length, 2);
  assert.match(voice.spoken[1], /knees are drifting out/);
});

test("Stop remains actionable during playback and voice releases resources on background and unmount", async () => {
  const voice = voiceHarness();
  await voice.enable();
  voice.options.camera.isSessionActive = true;
  for (let frame = 0; frame < 7; frame++) {
    voice.frame(pose(0.08));
    voice.advance(100);
  }
  assert.equal(voice.render().isSpeaking, true);
  await voice.command("stop");
  assert.equal(voice.counts().stops, 1);
  assert.equal(voice.render().isSpeaking, false);
  voice.background();
  assert.equal(voice.render().isListening, false);
  assert.equal(voice.counts().listeners, 0);
  await voice.command("start");
  assert.equal(voice.counts().starts, 0);
  voice.unmount();
  assert.equal(voice.counts().listeners, 0);
});
