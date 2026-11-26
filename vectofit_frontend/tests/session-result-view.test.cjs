const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");
const ts = require("typescript");

function harness(dev = true) {
  const cache = new Map();
  const hooks = [];
  const focusEvents = [];
  let cursor = 0;
  const element = (type, props) => ({ type, props: props ?? {} });
  const react = {
    useState(initial) {
      const index = cursor++;
      if (!(index in hooks)) hooks[index] = typeof initial === "function" ? initial() : initial;
      return [hooks[index], value => { hooks[index] = typeof value === "function" ? value(hooks[index]) : value; }];
    },
    useRef(initial) {
      const index = cursor++;
      if (!(index in hooks)) hooks[index] = { current: initial };
      return hooks[index];
    },
    useMemo: create => create(),
    useEffect() {},
    useId: () => "fixture-hatch",
  };
  const native = {
    ...Object.fromEntries(["Pressable", "ScrollView", "Text", "View", "Modal", "ActivityIndicator"].map(name => [name, name])),
    Animated: { View: "AnimatedView", Value: class { constructor(value) { this.value = value; } interpolate() { return this.value; } } },
    StyleSheet: { create: styles => styles, absoluteFill: { position: "absolute" } },
    Platform: { OS: "android" },
    AccessibilityInfo: { setAccessibilityFocus: node => focusEvents.push(node) },
    findNodeHandle: node => node?.nativeTag,
    PanResponder: { create: handlers => ({ panHandlers: handlers }) },
  };
  function load(filename) {
    const full = path.resolve(filename);
    if (cache.has(full)) return cache.get(full);
    const exports = {};
    cache.set(full, exports);
    const compiled = ts.transpileModule(fs.readFileSync(full, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX },
    }).outputText;
    vm.runInNewContext(compiled, {
      exports, __DEV__: dev, requestAnimationFrame: callback => callback(),
      require(request) {
        if (request === "react") return react;
        if (request === "react/jsx-runtime") return { jsx: element, jsxs: element, Fragment: "Fragment" };
        if (request === "react-native") return native;
        if (request === "react-native-safe-area-context") return { SafeAreaView: "SafeAreaView", useSafeAreaInsets: () => ({ bottom: 24 }) };
        if (request === "react-native-svg") return { __esModule: true, default: "Svg", Defs: "Defs", Path: "Path", Pattern: "Pattern", Rect: "Rect", Circle: "Circle", Line: "Line" };
        const base = path.resolve(path.dirname(full), request);
        return load(fs.existsSync(`${base}.tsx`) ? `${base}.tsx` : `${base}.ts`);
      },
    }, { filename: full });
    return exports;
  }
  const root = path.join(__dirname, "../src/features/session-results");
  const fixtures = load(path.join(root, "model/fixtures.ts"));
  const Component = load(path.join(root, "components/SessionResultView.tsx")).default;
  function render(props, component = Component) {
    cursor = 0;
    const nodes = [];
    function expand(node) {
      if (node == null || typeof node === "boolean") return "";
      if (Array.isArray(node)) return node.map(expand).join("");
      if (typeof node !== "object") return String(node);
      nodes.push(node);
      if (typeof node.type === "function") return expand(node.type(node.props));
      return expand(node.props.children);
    }
    const text = expand(element(component, props));
    return { text, nodes, find: predicate => nodes.find(predicate) };
  }
  return { render, fixture: fixtures.getSessionResultFixture, focusEvents,
    state: props => render(props, load(path.join(root, "components/SessionResultStateView.tsx")).default),
    preview: props => { cursor = 0; return load(path.join(root, "SessionResultPreview.tsx")).default(props); } };
}

function textOf(node) {
  if (node == null || typeof node === "boolean") return "";
  if (Array.isArray(node)) return node.map(textOf).join("");
  return typeof node === "object" ? textOf(node.props.children) : String(node);
}

function propsFor(result) {
  return { result, onBack() {}, onRecord() {}, onHistory() {} };
}

test("preview starts on the worst measured rep and bar/pill selection stays in sync", () => {
  const h = harness();
  const props = propsFor(h.fixture("main"));
  let screen = h.render(props);
  assert.match(screen.text, /6\/10 Reps/);
  assert.match(screen.text, /Development preview/);
  assert.equal(screen.find(node => node.props.testID === "rep-pill-7").props.accessibilityState.selected, true);
  screen.find(node => node.props.testID === "rep-bar-2").props.onPress();
  screen = h.render(props);
  assert.equal(screen.find(node => node.props.testID === "rep-pill-2").props.accessibilityState.selected, true);
  assert.match(screen.text, /Both knees stayed in line through this rep/);
  screen.find(node => node.props.testID === "rep-pill-7").props.onPress();
  screen = h.render(props);
  assert.match(screen.text, /Your right knee moved inward most during the ascent/);
});

test("unassessable selection shows the exclusion reason without fabricating a measurement", () => {
  const h = harness();
  const props = propsFor(h.fixture("unassessable"));
  let screen = h.render(props);
  assert.match(screen.text, /9 of 10 reps tracked/);
  screen.find(node => node.props.testID === "rep-pill-7").props.onPress();
  screen = h.render(props);
  assert.match(screen.text, /Your knee left the frame/);
  assert.match(screen.text, /Hatched = not measured/);
  assert.equal(screen.find(node => node.props.testID === "rep-pill-7").props.accessibilityLabel.includes("not measured"), true);
  assert.ok(!screen.text.includes("11°"));
});

test("each metric opens its matching explanation and closing restores the triggering target", () => {
  const h = harness();
  const props = propsFor(h.fixture("main"));
  let screen = h.render(props);
  const metric = screen.find(node => node.type === "Pressable" && node.props.accessibilityLabel?.startsWith("Right Knee"));
  metric.props.ref({ nativeTag: 42 });
  metric.props.onPress();
  screen = h.render(props);
  assert.equal(screen.find(node => node.type === "Modal").props.visible, true);
  assert.match(screen.text, /how far your right knee moved toward the middle/);
  assert.equal(screen.find(node => node.type === "SafeAreaView").props.importantForAccessibility, "no-hide-descendants");
  screen.find(node => node.type === "Pressable" && node.props.accessibilityLabel === "Close explanation").props.onPress();
  screen = h.render(props);
  assert.equal(screen.find(node => node.type === "Modal").props.visible, false);
  assert.equal(h.focusEvents.at(-1), 42);
});

test("bottom actions call their supplied navigation and measured height reserves scroll space", () => {
  const h = harness();
  const calls = [];
  const props = { ...propsFor(h.fixture("main")), onRecord: () => calls.push("record"), onHistory: () => calls.push("history") };
  let screen = h.render(props);
  screen.find(node => node.type === "View" && node.props.onLayout && node.props.style?.some?.(style => style?.position === "absolute")).props.onLayout({ nativeEvent: { layout: { height: 148 } } });
  screen = h.render(props);
  const scroll = screen.find(node => node.type === "ScrollView" && !node.props.horizontal);
  assert.equal(scroll.props.contentContainerStyle.at(-1).paddingBottom, 164);
  for (const label of ["Record next set", "View session history"]) {
    screen.find(node => node.type === "Pressable" && textOf(node) === label).props.onPress();
  }
  assert.equal(calls.join(","), "record,history");
});

test("rep targets remain at least 48dp and all statuses have text labels", () => {
  const h = harness();
  const screen = h.render(propsFor(h.fixture("main")));
  const pill = screen.find(node => node.props.testID === "rep-pill-1");
  const style = Object.assign({}, ...pill.props.style({ pressed: false }).filter(Boolean));
  assert.ok(style.width >= 48 && style.minHeight >= 48);
  const bar = screen.find(node => node.props.testID === "rep-bar-1");
  const barStyle = Object.assign({}, ...bar.props.style({ pressed: false }).filter(Boolean));
  assert.ok(barStyle.width >= 48 && barStyle.height >= 48);
  for (const label of ["Aligned", "Borderline", "Deviated", "Unassessable"]) assert.ok(screen.text.includes(label));
});

test("zero-assessable fixture remains unavailable rather than showing a positive verdict", () => {
  const h = harness();
  const screen = h.render(propsFor(h.fixture("zero_assessable")));
  assert.match(screen.text, /We couldn't assess any reps/);
  assert.ok(!screen.text.includes("Great alignment"));
  assert.ok(!screen.text.includes("All aligned"));
});

test("preview uses the existing parent tab for Home and the Insights stack for history", () => {
  const h = harness();
  const calls = [];
  const view = h.preview({ route: { params: { sessionId: 0, previewFixture: "main" } }, navigation: {
    popTo: name => calls.push(name),
    getParent: () => ({ navigate: name => calls.push(name) }),
  } });
  view.props.onRecord();
  view.props.onHistory();
  assert.equal(calls.join(","), "Home,SessionHistory");
  assert.equal(harness(false).preview({ route: { params: { sessionId: 0, previewFixture: "main" } } }), null);
});

function detailLayout(screen, width = 280) {
  screen.find(node => node.props.testID === "rep-detail-layout").props.onLayout({ nativeEvent: { layout: { width } } });
}

test("rep 7 opens at R 11 degrees and scrubbing synchronizes readouts, cursor and peak tag", () => {
  const h = harness();
  const props = propsFor(h.fixture("main"));
  let screen = h.render(props);
  detailLayout(screen);
  screen = h.render(props);
  assert.match(screen.text, /R 11°/);
  assert.match(screen.text, /PEAK/);
  assert.match(screen.text, /Skeleton unavailable for this rep/);
  assert.match(screen.text, /Off-track/);
  let scrubber = screen.find(node => node.props.testID === "phase-scrubber");
  assert.equal(scrubber.props.accessibilityValue.text, "2.2s, ascent");
  scrubber.props.onAccessibilityAction({ nativeEvent: { actionName: "decrement" } });
  screen = h.render(props);
  assert.match(screen.text, /R 8°/);
  assert.ok(!screen.text.includes("PEAK"));
  const cursor = screen.find(node => node.props.testID === "angle-cursor");
  assert.ok(Math.abs(cursor.props.x1 - (32 + 216 * 2100 / 2600)) < 1e-9);
  scrubber = screen.find(node => node.props.testID === "phase-scrubber");
  assert.equal(scrubber.props.accessibilityValue.now, 2100);
  screen.find(node => node.props.testID === "rep-pill-2").props.onPress();
  screen = h.render(props);
  assert.match(screen.text, /Timing unavailable for this rep/);
  screen.find(node => node.props.testID === "rep-pill-7").props.onPress();
  screen = h.render(props);
  assert.match(screen.text, /R 11°/);
  assert.equal(screen.find(node => node.props.testID === "phase-scrubber").props.accessibilityValue.now, 2200);
});

test("horizontal drags update time, vertical gestures do not claim the scroll, and release stops changes", () => {
  const h = harness();
  const props = propsFor(h.fixture("main"));
  let screen = h.render(props);
  detailLayout(screen);
  screen = h.render(props);
  const scrubber = screen.find(node => node.props.testID === "phase-scrubber");
  assert.equal(scrubber.props.onStartShouldSetPanResponder(), false);
  assert.equal(scrubber.props.onMoveShouldSetPanResponder(null, { dx: 10, dy: 20 }), false);
  assert.equal(scrubber.props.onMoveShouldSetPanResponder(null, { dx: 20, dy: 2 }), true);
  scrubber.props.ref.current = { measureInWindow: callback => callback(100, 0, 280, 96) };
  scrubber.props.onPanResponderGrant(null, { moveX: 240 });
  screen = h.render(props);
  assert.equal(screen.find(node => node.props.testID === "phase-scrubber").props.accessibilityValue.now, 1300);
  scrubber.props.onPanResponderMove(null, { moveX: 9000 });
  screen = h.render(props);
  assert.equal(screen.find(node => node.props.testID === "phase-scrubber").props.accessibilityValue.now, 2600);
  scrubber.props.onPanResponderRelease();
  scrubber.props.onPanResponderMove(null, { moveX: 100 });
  screen = h.render(props);
  assert.equal(screen.find(node => node.props.testID === "phase-scrubber").props.accessibilityValue.now, 2600);
});

test("provided landmark frames drive the skeleton while angle values still come from the series", () => {
  const h = harness();
  const result = h.fixture("main");
  const points = { nose: [0.5, 0.1], lShoulder: [0.35, 0.25], rShoulder: [0.65, 0.25],
    lHip: [0.4, 0.5], rHip: [0.6, 0.5], lKnee: [0.35, 0.7], rKnee: [0.65, 0.7],
    lAnkle: [0.3, 0.9], rAnkle: [0.7, 0.9] };
  result.reps[6].frames = [{ tMs: 2200, pts: points }, { tMs: 1400, pts: { ...points, rKnee: [0.8, 0.7] } }];
  const props = propsFor(result);
  let screen = h.render(props);
  detailLayout(screen);
  screen = h.render(props);
  assert.ok(!screen.text.includes("Skeleton unavailable for this rep"));
  assert.match(screen.text, /R 11°/);
  const originalLeg = screen.find(node => node.type === "Path" && node.props.stroke === "#F43F5E").props.d;
  const scrubber = screen.find(node => node.props.testID === "phase-scrubber");
  scrubber.props.ref.current = { measureInWindow: callback => callback(100, 0, 280, 96) };
  scrubber.props.onPanResponderGrant(null, { moveX: 132 + 216 * 1400 / 2600 });
  screen = h.render(props);
  assert.match(screen.text, /R 3°/);
  const newLeg = screen.find(node => node.type === "Path" && node.props.stroke === "#F43F5E").props.d;
  assert.notEqual(newLeg, originalLeg);
});

test("excluded repetitions show only their detail header and exclusion copy", () => {
  const h = harness();
  const props = propsFor(h.fixture("unassessable"));
  let screen = h.render(props);
  screen.find(node => node.props.testID === "rep-pill-7").props.onPress();
  screen = h.render(props);
  assert.match(screen.text, /Your knee left the frame/);
  assert.equal(screen.find(node => node.props.testID === "phase-scrubber"), undefined);
  assert.equal(screen.find(node => node.props.testID === "angle-line-chart"), undefined);
});

test("a late measurement callback cannot move the playhead after a drag ends", () => {
  const h = harness();
  const props = propsFor(h.fixture("main"));
  let screen = h.render(props);
  detailLayout(screen);
  screen = h.render(props);
  const scrubber = screen.find(node => node.props.testID === "phase-scrubber");
  let measured;
  scrubber.props.ref.current = { measureInWindow: callback => { measured = callback; } };
  scrubber.props.onPanResponderGrant(null, { moveX: 100 });
  scrubber.props.onPanResponderRelease();
  measured(100, 0, 280, 96);
  screen = h.render(props);
  assert.equal(screen.find(node => node.props.testID === "phase-scrubber").props.accessibilityValue.now, 2200);
});

test("loading is indeterminate, has no rep count, and keeps history available", () => {
  const h = harness();
  const screen = h.state({ state: { status: "loading" }, retry: async () => {}, ...propsFor(null) });
  assert.match(screen.text, /Analyzing your reps\.\.\./);
  assert.ok(!/\d+ REPS/.test(screen.text));
  const progress = screen.find(node => node.props.accessibilityRole === "progressbar");
  assert.equal(progress.props.accessibilityValue, undefined);
  const record = screen.find(node => node.type === "Pressable" && textOf(node) === "Processing session...");
  assert.equal(record.props.disabled, true);
  assert.equal(record.props.onPress, undefined);
  assert.ok(screen.find(node => node.type === "Pressable" && textOf(node) === "View session history"));
  assert.ok(!screen.text.includes("Counting reps"));
});

test("loading steps are shown only when a real stage is supplied", () => {
  const h = harness();
  const screen = h.state({ state: { status: "loading", stage: "counting" }, retry: async () => {}, ...propsFor(null) });
  for (const step of ["Tracking your body", "Counting reps", "Checking knee alignment"]) assert.ok(screen.text.includes(step));
  assert.ok(screen.find(node => node.props.accessibilityLiveRegion === "polite" && node.props.accessibilityLabel === "Counting reps"));
});

test("error copy never claims a saved session without confirmation and retry calls its callback", () => {
  for (const [kind, body] of [["network", "Check your connection"], ["processing_failed", "Something went wrong"], ["unknown", "Something went wrong"]]) {
    const h = harness();
    let calls = 0;
    const screen = h.state({ state: { status: "error", error: { kind } }, retry: async () => { calls++; }, ...propsFor(null) });
    assert.match(screen.text, /We couldn't finish analyzing this session/);
    assert.ok(screen.text.includes(body));
    assert.ok(!screen.text.includes("Your session data was saved"));
    screen.find(node => node.type === "Pressable" && textOf(node) === "Try again").props.onPress();
    assert.equal(calls, 1);
  }
  const confirmed = harness().state({ state: { status: "error", error: { kind: "processing_failed", sessionSaved: true } }, retry: async () => {}, ...propsFor(null) });
  assert.match(confirmed.text, /Your session data was saved/);
});

test("retry remains busy and disabled without a spinning indicator under reduced motion", () => {
  const h = harness();
  const screen = h.state({ state: { status: "error", error: { kind: "network" } }, retrying: true, retry: async () => {}, ...propsFor(null) });
  const retry = screen.find(node => node.type === "Pressable" && textOf(node) === "Try again");
  assert.equal(retry.props.disabled, true);
  assert.equal(retry.props.accessibilityState.busy, true);
  assert.equal(screen.find(node => node.type === "ActivityIndicator"), undefined);
});

test("zero-assessable results hide measurements and charts, while limited tracking shows its caveat", () => {
  const empty = harness();
  const screen = empty.render(propsFor(empty.fixture("zero_assessable")));
  assert.equal(screen.find(node => node.props.testID === "rep-pill-1"), undefined);
  assert.equal(screen.find(node => node.props.testID === "rep-detail-card"), undefined);
  assert.ok(!screen.text.includes("Left Knee"));
  const limited = harness();
  const warning = limited.render(propsFor(limited.fixture("limited")));
  assert.match(warning.text, /Tracking was weak in this set/);
  assert.match(warning.text, /6 of 10 reps tracked/);
});

test("the development picker selects states, retries asynchronously, and ignores a stale retry", async () => {
  const h = harness();
  const props = { route: { params: { sessionId: 0, previewFixture: "main" } }, navigation: {} };
  let preview = h.preview(props);
  preview.props.controls.props.onSelect("network_error");
  preview = h.preview(props);
  assert.equal(preview.props.state.error.kind, "network");
  const retry = preview.props.retry();
  assert.equal(h.preview(props).props.retrying, true);
  await retry;
  assert.equal(h.preview(props).props.state.status, "ready");
  preview = h.preview(props);
  preview.props.controls.props.onSelect("processing_failed");
  preview = h.preview(props);
  const stale = preview.props.retry();
  preview.props.controls.props.onSelect("zero_assessable");
  await stale;
  assert.equal(h.preview(props).props.state.data.summary.assessableReps, 0);
  preview = h.preview(props);
  preview.props.controls.props.onSelect("checking");
  assert.equal(h.preview(props).props.state.stage, "checking");
});

test("live signed angles preserve outward movement, model disagreement and source-specific copy", () => {
  const h = harness();
  const result = h.fixture("main");
  result.signedAngles = true;
  result.capture.mirrored = null;
  result.presentation = { headline: "Outward knee movement was measured.", cues: [], modelDisagreement: true };
  const rep = result.reps[6];
  rep.worstPeakDeg = -11;
  rep.peakDeg.right = -11;
  rep.series.rightDeg = [-1, -3, -5, -11, -9];
  rep.modelEvidence = { label: "good", confidence: 0.82, disagrees: true };
  rep.insight = "Your right knee moved outward during this rep.";
  const props = { ...propsFor(result), preview: false };
  let screen = h.render(props);
  detailLayout(screen);
  screen = h.render(props);
  assert.match(screen.text, /R -11°/);
  assert.match(screen.text, /Outward knee movement/);
  assert.match(screen.text, /Model knee alignment: Good/);
  assert.match(screen.text, /Confidence 82%/);
  assert.match(screen.text, /Results disagree/);
  assert.ok(!screen.text.includes("Push your knees out"));
  assert.ok(!screen.text.includes("Development preview"));
  assert.ok(!screen.text.includes("Peak inward angle"));
});
