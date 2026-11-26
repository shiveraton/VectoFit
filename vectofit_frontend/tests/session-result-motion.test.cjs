const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");
const ts = require("typescript");

function runner() {
  const slots = [], effects = [], animations = [], loops = [];
  const cache = new Map();
  let cursor = 0, resolvePreference, rejectPreference, preferenceListener, removed = false;
  const preference = new Promise((resolve, reject) => { resolvePreference = resolve; rejectPreference = reject; });
  const react = {
    useState(initial) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = typeof initial === "function" ? initial() : initial;
      return [slots[index], value => { slots[index] = typeof value === "function" ? value(slots[index]) : value; }];
    },
    useRef(initial) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = { current: initial };
      return slots[index];
    },
    useEffect(create, deps) {
      const index = cursor++;
      const previous = slots[index];
      if (!previous || deps.some((value, i) => !Object.is(value, previous.deps[i]))) {
        effects.push(() => { previous?.cleanup?.(); slots[index] = { deps, cleanup: create() }; });
      }
    },
  };
  class Value {
    constructor(value) { this.value = value; this.listeners = new Map(); this.next = 0; }
    setValue(value) { this.value = value; for (const listener of this.listeners.values()) listener({ value }); }
    addListener(listener) { const key = String(this.next++); this.listeners.set(key, listener); return key; }
    removeListener(key) { this.listeners.delete(key); }
    interpolate() { return this.value; }
  }
  const native = {
    AccessibilityInfo: {
      isReduceMotionEnabled: () => preference,
      addEventListener: (_, listener) => { preferenceListener = listener; return { remove: () => { removed = true; } }; },
    },
    Animated: {
      Value, View: "AnimatedView",
      timing(value, options) {
        const animation = { value, options, stopped: false, start() { this.started = true; }, stop() { this.stopped = true; } };
        animations.push(animation); return animation;
      },
      loop(animation) {
        const loop = { stopped: false, start() { animation.start(); }, stop() { this.stopped = true; animation.stop(); } };
        loops.push(loop); return loop;
      },
    },
    StyleSheet: { create: styles => styles }, View: "View", Text: "Text",
  };
  function load(filename) {
    filename = path.resolve(filename);
    if (cache.has(filename)) return cache.get(filename);
    const exports = {};
    cache.set(filename, exports);
    const code = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX },
    }).outputText;
    vm.runInNewContext(code, { exports, require(request) {
      if (request === "react") return react;
      if (request === "react-native") return native;
      if (request === "react/jsx-runtime") return { jsx: (type, props) => ({ type, props }), jsxs: (type, props) => ({ type, props }) };
      const base = path.resolve(path.dirname(filename), request);
      return load(fs.existsSync(`${base}.tsx`) ? `${base}.tsx` : `${base}.ts`);
    } }, { filename });
    return exports;
  }
  const root = path.join(__dirname, "../src/features/session-results");
  return {
    load: name => load(path.join(root, name)).default,
    run(hook, ...args) { cursor = 0; const value = hook(...args); while (effects.length) effects.shift()(); return value; },
    dispose() { for (const slot of slots) slot?.cleanup?.(); },
    animations, loops,
    resolvePreference: value => resolvePreference(value), rejectPreference: () => rejectPreference(new Error("Unavailable")),
    preferenceChanged: value => preferenceListener(value), removed: () => removed,
  };
}

test("motion stays reduced until the device preference resolves, then follows changes and unsubscribes", async () => {
  const r = runner();
  const hook = r.load("hooks/useReducedMotion.ts");
  assert.equal(r.run(hook), true);
  r.resolvePreference(false);
  await Promise.resolve();
  assert.equal(r.run(hook), false);
  r.preferenceChanged(true);
  assert.equal(r.run(hook), true);
  r.dispose();
  assert.equal(r.removed(), true);
});

test("a newer preference event wins over a delayed query, and query failure remains static", async () => {
  const r = runner();
  const hook = r.load("hooks/useReducedMotion.ts");
  r.run(hook);
  r.preferenceChanged(true);
  r.resolvePreference(false);
  await Promise.resolve();
  assert.equal(r.run(hook), true);
  const failed = runner();
  const fallback = failed.load("hooks/useReducedMotion.ts");
  failed.run(fallback);
  failed.rejectPreference();
  await Promise.resolve(); await Promise.resolve();
  assert.equal(failed.run(fallback), true);
});

test("count-up lasts 600ms, shows integer values, and becomes final immediately under reduced motion", () => {
  const r = runner();
  const hook = r.load("hooks/useCountUp.ts");
  r.run(hook, 6, false);
  assert.equal(r.animations[0].options.duration, 600);
  assert.equal(r.run(hook, 6, false), 0);
  r.animations[0].value.setValue(3.2);
  assert.equal(r.run(hook, 6, false), 3);
  assert.equal(r.run(hook, 6, true), 6);
  assert.equal(r.animations[0].stopped, true);
  assert.equal(r.animations[0].value.listeners.size, 0);
});

test("reduced-motion count-up never starts an animation", () => {
  const r = runner();
  assert.equal(r.run(r.load("hooks/useCountUp.ts"), 6, true), 6);
  assert.equal(r.animations.length, 0);
});

test("a delayed motion preference does not roll the already displayed count back to zero", () => {
  const r = runner();
  const hook = r.load("hooks/useCountUp.ts");
  assert.equal(r.run(hook, 6, true), 6);
  assert.equal(r.run(hook, 6, false), 6);
  assert.equal(r.animations.length, 0);
});

test("selection scrolling lasts 200ms, stays synchronized, and resumes from manual scroll positions", () => {
  const r = runner();
  const hook = r.load("hooks/useSelectionScroll.ts");
  const chart = [], pills = [];
  const chartRef = { current: { scrollTo: value => chart.push(value.x) } };
  const pillRef = { current: { scrollTo: value => pills.push(value.x) } };
  let handlers = r.run(hook, chartRef, pillRef, { chart: 100, pills: 200 }, false);
  assert.equal(r.animations[0].options.duration, 200);
  r.animations[0].value.setValue(0.5);
  assert.equal(chart.at(-1), 50);
  assert.equal(pills.at(-1), 100);
  handlers.onDragStart();
  assert.equal(r.animations[0].stopped, true);
  handlers.onChartScroll({ nativeEvent: { contentOffset: { x: 80 } } });
  handlers.onPillsScroll({ nativeEvent: { contentOffset: { x: 100 } } });
  handlers = r.run(hook, chartRef, pillRef, { chart: 120, pills: 240 }, false);
  r.animations[1].value.setValue(0.5);
  assert.equal(chart.at(-1), 100);
  assert.equal(pills.at(-1), 170);
  r.dispose();
  assert.equal(r.animations[1].value.listeners.size, 0);
});

test("reduced motion jumps to selection and cancels in-flight scroll animation", () => {
  const r = runner();
  const hook = r.load("hooks/useSelectionScroll.ts");
  const calls = [];
  const ref = { current: { scrollTo: value => calls.push(value.x) } };
  r.run(hook, ref, ref, { chart: 80, pills: 120 }, true);
  assert.equal(r.animations.length, 0);
  assert.equal(calls.at(-1), 120);
  r.run(hook, ref, ref, { chart: 100, pills: 200 }, false);
  r.run(hook, ref, ref, { chart: 100, pills: 200 }, true);
  assert.equal(r.animations[0].stopped, true);
  assert.equal(calls.at(-1), 200);
  const count = calls.length;
  r.animations[0].value.setValue(0.2);
  assert.equal(calls.length, count);
});

test("loading shimmer uses an indeterminate native animation and stops when motion is reduced", () => {
  const r = runner();
  const loading = r.load("components/LoadingContent.tsx");
  r.run(loading, { reducedMotion: false });
  assert.equal(r.animations[0].options.useNativeDriver, true);
  assert.equal(r.animations[0].options.duration, 1200);
  assert.equal(r.loops.length, 1);
  r.run(loading, { reducedMotion: true });
  assert.equal(r.loops[0].stopped, true);
  assert.equal(r.loops.length, 1);
});
