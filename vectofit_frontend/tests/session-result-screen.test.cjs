const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");
const ts = require("typescript");

const filename = path.join(__dirname, "../src/screens/SessionResultScreen.tsx");
const source = fs.readFileSync(filename, "utf8");
const compiled = ts.transpileModule(
  `${source}\nexport { CoachingContent };`,
  {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      jsx: ts.JsxEmit.React,
      esModuleInterop: true,
    },
  },
).outputText;

function renderSession(reps, findings = [], selectedIndex = 0) {
  const react = {
    createElement: (type, props, ...children) => ({
      type,
      props: { ...props, children },
    }),
    Fragment: "Fragment",
    useState: (initial) => [typeof initial === "number" ? selectedIndex : initial, () => {}],
  };
  const styles = new Proxy({}, { get: (_, key) => key });
  const context = {
    exports: {},
    require(name) {
      if (name === "react") return react;
      if (name === "react-native") {
        return Object.fromEntries(
          ["ActivityIndicator", "Image", "Pressable", "ScrollView", "Text", "View"].map(
            (name) => [name, name],
          ),
        );
      }
      if (name === "react-native-safe-area-context") return { SafeAreaView: "SafeAreaView" };
      if (name.endsWith("useAuthStore")) return { default: (select) => select({ token: null }), __esModule: true };
      if (name.endsWith("sessionStructure")) return { getAssessmentRepSnapshotUrl: (id) => `/snapshot/${id}` };
      if (name.endsWith("designTokens")) return { COLORS: {} };
      if (name.endsWith("SessionResultScreenStyles")) return { default: styles, __esModule: true };
      throw new Error(`Unexpected import ${name}`);
    },
  };
  vm.runInNewContext(compiled, context, { filename });

  const nodes = [];
  function expand(node) {
    if (node == null || typeof node === "boolean") return "";
    if (Array.isArray(node)) return node.map(expand).join("");
    if (typeof node !== "object") return String(node);
    if (typeof node.type === "function") return expand(node.type(node.props));
    nodes.push(node);
    return expand(node.props.children);
  }
  const text = expand(context.exports.CoachingContent({ session: { reps, report: { findings } } }));
  const chips = nodes.filter((node) => node.type === "Pressable");
  return { text, chips };
}

function repetition(predictedClass, deviation = false, id = 1) {
  return {
    id,
    rep_number: id,
    analysis_result: {
      model_prediction: {
        status: "assessed",
        prediction_target: "knee_alignment",
        view_angle: "frontal",
        predicted_class: predictedClass,
        probability: 0.82,
      },
      fppa: {
        status: "assessed",
        cutoff_degrees: 10,
        knees: {
          left: { peak_degrees: deviation ? 15 : 5, state: deviation ? "deviation" : "aligned", direction: deviation ? "inward" : null },
          right: { peak_degrees: 3, state: "aligned", direction: null },
        },
      },
    },
  };
}

const finding = {
  code: "VALGUS_LEFT",
  affected_reps: [1],
  severity: "minor",
  summary: "Left knee exceeded the inward FPPA cutoff.",
  cue: "Keep the left knee tracking over the left foot.",
};

test("agreement displays model class, confidence, FPPA and matching coaching", () => {
  const good = renderSession([repetition("good")]);
  assert.match(good.text, /1 assessed \| 0 unassessed/);
  assert.match(good.text, /1 good \| 0 bad/);
  assert.match(good.text, /Model confidence: 82%/);
  assert.match(good.chips[0].props.accessibilityLabel, /Good/);
  assert.equal(good.chips[0].props.style[1], "repChipGood");

  const bad = renderSession([repetition("bad", true)], [finding]);
  assert.match(bad.text, /0 good \| 1 bad/);
  assert.match(bad.text, /FPPA-based coaching/);
  assert.ok(bad.text.includes(finding.cue));
  assert.equal(bad.chips[0].props.style[1], "repChipBad");
});

for (const [label, deviation] of [["good", true], ["bad", false]]) {
  test(`disagreement for model ${label} preserves both results and requests review`, () => {
    const { text } = renderSession([repetition(label, deviation)], [finding]);
    assert.match(text, /Results disagree/);
    assert.match(text, /Review conflicting results/);
    assert.ok(text.includes(`Model knee alignment: ${label === "good" ? "Good" : "Bad"}`));
    assert.ok(text.includes(`FPPA threshold result · ${deviation ? "Deviation" : "Aligned"}`));
    assert.ok(!text.includes(finding.cue));
  });
}

test("mixed results count assessed and unassessed without counting missing predictions as good", () => {
  const missing = repetition("good", false, 3);
  delete missing.analysis_result.model_prediction;
  const { text, chips } = renderSession([repetition("good"), repetition("bad", true, 2), missing], [], 2);
  assert.match(text, /2 assessed \| 1 unassessed/);
  assert.match(text, /1 good \| 1 bad/);
  assert.match(text, /Model knee alignment assessment unavailable/);
  assert.equal(chips[2].props.style[1], "repChipUnavailable");
});

test("unavailable inference, unsupported views and legacy output show unavailable", () => {
  const unavailable = repetition("good");
  unavailable.analysis_result.model_prediction.status = "not_assessed";
  const unsupported = repetition("good");
  unsupported.analysis_result.model_prediction.view_angle = "sagittal";
  unsupported.analysis_result.fppa = { status: "not_assessed", reason: "view_not_supported" };
  for (const rep of [unavailable, unsupported, { id: 1, rep_number: 1, analysis_result: null }]) {
    const { text, chips } = renderSession([rep], [finding]);
    assert.match(text, /Assessment unavailable/);
    assert.match(text, /0 assessed \| 1 unassessed/);
    assert.match(text, /0 good \| 0 bad/);
    assert.ok(!text.includes("Results disagree"));
    assert.equal(chips[0].props.style[1], "repChipUnavailable");
  }
  assert.match(renderSession([unsupported]).text, /requires a frontal camera view/);
});

test("malformed predictions and invalid FPPA measurements are handled independently", () => {
  for (const probability of [null, undefined, NaN, Infinity, -0.1, 1.1, "0.8"]) {
    const rep = repetition("good");
    rep.analysis_result.model_prediction.probability = probability;
    assert.match(renderSession([rep]).text, /0 assessed \| 1 unassessed/);
  }
  const rep = repetition("bad", true);
  rep.analysis_result.fppa.knees.left.peak_degrees = NaN;
  const { text } = renderSession([rep], [finding]);
  assert.match(text, /1 assessed \| 0 unassessed/);
  assert.match(text, /FPPA measurements unavailable/);
  assert.ok(!text.includes(finding.cue));
});

test("empty session explicitly shows unavailable and zero totals", () => {
  const { text, chips } = renderSession([]);
  assert.match(text, /Assessment unavailable/);
  assert.match(text, /0 assessed \| 0 unassessed/);
  assert.equal(chips.length, 0);
});
