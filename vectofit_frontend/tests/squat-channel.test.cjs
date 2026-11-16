const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");
const ts = require("typescript");

function loadModule(relativePath, imports) {
  const filename = path.join(__dirname, "../src", relativePath);
  const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.React, esModuleInterop: true },
  }).outputText;
  const context = { exports: {}, FormData: class { append() {} }, console: { info() {}, error() {} }, require(name) {
    assert.ok(name in imports, `Unexpected import ${name}`);
    return imports[name];
  } };
  vm.runInNewContext(compiled, context, { filename });
  return context.exports;
}

function deferred() {
  let resolve;
  const promise = new Promise((complete) => { resolve = complete; });
  return { promise, resolve };
}

function cameraHarness() {
  const state = [];
  const refs = [];
  let stateIndex = 0;
  let refIndex = 0;
  let frame;
  let finished;
  let createCount = 0;
  let stopCount = 0;
  let uploadCount = 0;
  let detailCount = 0;
  let failDetail = true;
  const creation = deferred();
  const session = { id: 42, status: "PROCESSING", reps: [], rep_count: 0 };
  const recorder = {
    async startRecording(onFinished) { finished = onFinished; },
    async stopRecording() { stopCount++; finished("/recording.mp4", "stopped"); },
  };
  class AssessmentUploadUncertainError extends Error {}
  const service = {
    AssessmentUploadUncertainError,
    getAssessmentUploadErrorMessage: (error) => error.message,
    async uploadSquatAssessmentVideo(file, exercise, view, onCreated) {
      uploadCount++;
      onCreated(42);
      throw new Error("Detail request failed");
    },
    async getSquatAssessmentSession(id) {
      detailCount++;
      assert.equal(id, 42);
      if (failDetail) throw new Error("Still offline");
      return session;
    },
  };
  const react = {
    useState(initial) {
      const index = stateIndex++;
      if (!(index in state)) state[index] = initial;
      return [state[index], (next) => {
        state[index] = typeof next === "function" ? next(state[index]) : next;
      }];
    },
    useRef(initial) {
      const index = refIndex++;
      if (!(index in refs)) refs[index] = { current: initial };
      return refs[index];
    },
    useCallback: (callback) => callback,
    useEffect() {},
  };
  const module = loadModule("features/squat/hooks/useCameraPoseScreen.ts", {
    react,
    "@react-navigation/native": { useIsFocused: () => true },
    "react-native-worklets": { scheduleOnRN: (callback, ...args) => callback(...args) },
    "react-native-vision-camera": {
      useCameraDevice: () => ({}),
      useCameraPermission: () => ({ hasPermission: true, canRequestPermission: false }),
      useFrameOutput: (options) => { frame = options.onFrame; return {}; },
      useVideoOutput: () => ({ createRecorder: () => { createCount++; return creation.promise; } }),
    },
    "../services/assessmentSessionService": service,
    "../../calibration/services/poseLandmarker": {
      poseLandmarkerPlugin: { detect: () => Array.from({ length: 33 }, () => [0.5, 0.5, 0, 1]).flat() },
    },
  });
  function render() {
    stateIndex = 0;
    refIndex = 0;
    return module.useCameraPoseScreen("bodyweight_squat", "frontal");
  }
  return {
    render,
    ready() {
      render().handleCameraConfigured();
      frame({ width: 720, height: 1280, dispose() {} });
    },
    completeCreation: () => creation.resolve(recorder),
    restoreNetwork: () => { failDetail = false; },
    counts: () => ({ createCount, stopCount, uploadCount, detailCount }),
  };
}

test("start requires a visible body and configured camera", async () => {
  const camera = cameraHarness();
  await camera.render().startSession();
  camera.render().handleCameraConfigured();
  await camera.render().startSession();
  assert.equal(camera.counts().createCount, 0);
});

test("rapid Start calls create one recorder and Flip stays locked through startup and recording", async () => {
  const camera = cameraHarness();
  camera.ready();
  const starting = camera.render().startSession();
  await camera.render().startSession();
  await camera.render().toggleCameraFacing();
  assert.equal(camera.render().cameraFacing, "front");
  assert.equal(camera.render().isStartingSession, true);
  assert.equal(camera.counts().createCount, 1);
  camera.completeCreation();
  await starting;
  await camera.render().toggleCameraFacing();
  assert.equal(camera.render().cameraFacing, "front");
  assert.equal(camera.render().isSessionActive, true);
  assert.equal(camera.counts().stopCount, 0);
});

test("repeated End and retry calls retain the created session and avoid duplicate uploads", async () => {
  const camera = cameraHarness();
  camera.ready();
  const starting = camera.render().startSession();
  camera.completeCreation();
  await starting;
  await Promise.all([camera.render().stopSession(), camera.render().stopSession()]);
  assert.equal(camera.counts().stopCount, 1);
  assert.equal(camera.counts().uploadCount, 1);
  assert.equal(camera.render().recordedVideoPath, "/recording.mp4");
  await camera.render().retryAssessment();
  camera.restoreNetwork();
  await camera.render().retryAssessment();
  assert.equal(camera.counts().uploadCount, 1);
  assert.equal(camera.counts().detailCount, 2);
  assert.equal(camera.render().savedSession.status, "PROCESSING");
  assert.match(camera.render().savedAssessmentMessage, /processing/);
  assert.doesNotMatch(camera.render().savedAssessmentMessage, /0 reps detected/);
});

function serviceHarness(post) {
  let detailCount = 0;
  const api = {
    async get(url) {
      if (url === "/exercises/variants/") {
        return { data: [{ id: 1, variant_type: "BW", is_active: true }] };
      }
      detailCount++;
      throw new Error("Detail offline");
    },
    post,
  };
  const module = loadModule("features/squat/services/assessmentSessionService.ts", {
    "../../../api/client": { default: api, __esModule: true },
    axios: { isAxiosError: (error) => error.isAxiosError === true },
  });
  return { module, detailCount: () => detailCount };
}

test("upload exposes the created ID before a failed detail fetch", async () => {
  const service = serviceHarness(async () => ({ data: { id: 42 } }));
  let createdId;
  await assert.rejects(service.module.uploadSquatAssessmentVideo("/video.mp4", "bodyweight_squat", "frontal", (id) => { createdId = id; }));
  assert.equal(createdId, 42);
  assert.equal(service.detailCount(), 1);
});

test("ambiguous upload failures require checking Insights before another upload", async () => {
  const service = serviceHarness(async () => { throw { isAxiosError: true }; });
  await assert.rejects(
    service.module.uploadSquatAssessmentVideo("/video.mp4", "bodyweight_squat", "frontal"),
    (error) => error instanceof service.module.AssessmentUploadUncertainError,
  );
});

test("contained landmarks preserve the whole source frame and front-camera mirroring", () => {
  const react = { createElement: (type, props, ...children) => ({ type, props, children }) };
  const overlay = loadModule("features/squat/components/PoseLandmarkOverlay.tsx", {
    react,
    "react-native": { StyleSheet: { absoluteFill: {} }, View: "View" },
    "react-native-svg": { default: "Svg", Circle: "Circle", Line: "Line", __esModule: true },
  }).default;
  const landmarks = Array.from({ length: 33 }, (_, id) => ({
    id, x_coordinate: 0, y_coordinate: 0, visibility: 1,
  }));
  for (const mirrored of [false, true]) {
    const tree = overlay({ landmarks, viewportWidth: 360, viewportHeight: 300,
      sourceFrameWidth: 720, sourceFrameHeight: 1280, mirrored });
    const joints = tree.children[0].children[1];
    assert.equal(joints[0].props.cy, 0);
    assert.equal(joints[0].props.cx, mirrored ? 264.375 : 95.625);
  }
});
