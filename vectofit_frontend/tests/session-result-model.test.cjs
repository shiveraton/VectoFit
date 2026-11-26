const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");
const ts = require("typescript");

function loadModel(dev = true) {
  const cache = new Map();
  function load(filename) {
    if (cache.has(filename)) return cache.get(filename);
    const exports = {};
    cache.set(filename, exports);
    const compiled = ts.transpileModule(fs.readFileSync(filename, "utf8"), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
    }).outputText;
    vm.runInNewContext(compiled, {
      exports, __DEV__: dev,
      require: request => load(path.resolve(path.dirname(filename), `${request}.ts`)),
    }, { filename });
    return exports;
  }
  const model = path.join(__dirname, "../src/features/session-results/model");
  return {
    ...load(path.join(model, "selectors.ts")),
    ...load(path.join(model, "detail.ts")),
    ...load(path.join(model, "fixtures.ts")),
    ...load(path.join(model, "validation.ts")),
    ...load(path.join(model, "status.ts")),
  };
}

const m = loadModel();
const fixture = name => m.getSessionResultFixture(name ?? "main");

test("main fixture preserves supplied peaks, labels, summary and rep 7 timing", () => {
  const main = fixture();
  assert.equal(main.reps.map(rep => rep.worstPeakDeg).join(","), "3,2,3,4,6,4,11,8,7,3");
  assert.equal(main.summary.counts.aligned, 6);
  assert.equal(main.summary.balanceDeg, 8);
  assert.equal(main.reps[6].series.rightDeg.join(","), "1,3,5,11,9");
  assert.equal(main.reps[6].peakAtMs, 2200);
});

test("all fixture variants pass development invariants and are isolated from mutations", () => {
  for (const name of ["main", "unassessable", "all_aligned", "zero_assessable", "limited"]) {
    assert.doesNotThrow(() => m.assertSessionResult(fixture(name)));
  }
  fixture().reps[0].kneeStatus.left = "deviated";
  assert.equal(fixture().reps[0].kneeStatus.left, "aligned");
});

test("fixtures are blocked outside development", () => {
  assert.throws(() => loadModel(false).getSessionResultFixture("main"), /only in development/);
});

test("tier and headline use assessable coverage and supplied knee states", () => {
  const main = fixture();
  assert.equal(m.selectTier(main).label, "Mostly aligned");
  assert.equal(m.selectTier(main).headline, "Mostly solid. Right knee drifted inward on 3 reps.");
  assert.equal(m.selectTier(fixture("all_aligned")).headline, "Clean set. Both knees tracked in line.");
  assert.equal(m.selectTier(fixture("zero_assessable")).kind, "empty");
  main.summary.counts.aligned = 5;
  assert.equal(m.selectTier(main).label, "Needs work");
  assert.match(m.selectTier(main).headline, /right knee.*3 reps/);
});

test("focus side uses deviation counts before peak magnitude", () => {
  const main = fixture();
  main.summary.left.worstPeakDeg = 100;
  assert.equal(m.selectFocusSide(main), "right");
  main.reps.forEach(rep => { rep.kneeStatus.right = "aligned"; });
  assert.equal(m.selectFocusSide(main), "left");
});

test("borderline-only sessions identify the affected knee instead of reporting zero reps", () => {
  const main = fixture();
  main.reps.forEach(rep => { rep.kneeStatus = { left: "aligned", right: "aligned" }; });
  main.reps[4].kneeStatus.right = "borderline";
  main.summary.left.worstPeakDeg = 100;
  assert.equal(m.selectFocusSide(main), "right");
  assert.match(m.selectTier(main).headline, /Right knee.*1 rep\./);
});

test("comparison supports improvement, equality, decline and absent history", () => {
  const main = fixture();
  assert.equal(m.selectComparison(main), "+2 aligned vs last set");
  main.summary.previousAlignedCount = 6;
  assert.equal(m.selectComparison(main), "Same as last set");
  main.summary.previousAlignedCount = 8;
  assert.equal(m.selectComparison(main), "2 fewer aligned vs last set");
  main.summary.previousAlignedCount = null;
  assert.equal(m.selectComparison(main), null);
});

test("tracking boundaries and zero coverage do not fabricate visibility", () => {
  const main = fixture();
  assert.equal(m.selectTracking(main).caption, "All reps clearly visible");
  assert.equal(m.selectTracking(fixture("unassessable")).caption, "9 of 10 reps tracked");
  for (const [count, label] of [[9, "Good"], [7, "Fair"], [6, "Limited"], [0, "Limited"]]) {
    main.summary.assessableReps = count;
    assert.equal(m.selectTracking(main).label, label);
  }
  main.summary.totalReps = 0;
  assert.equal(m.selectTracking(main).caption, "0 of 0 reps tracked");
});

test("balance fill is symmetric, capped and distinct from unavailable", () => {
  assert.ok(Math.abs(m.balanceFillPct(8, 12) - 100 / 3) < 1e-9);
  assert.equal(m.balanceFillPct(-8, 12), m.balanceFillPct(8, 12));
  assert.equal(m.balanceFillPct(20, 12), 50);
  assert.equal(m.balanceFillPct(0, 12), 0);
  assert.equal(m.balanceFillPct(null, 12), null);
  assert.equal(m.balanceFillPct(8, 0), null);
  assert.equal(m.selectBalanceCaption(-5), "Left knee drifts 5° more");
  assert.equal(m.selectBalanceCaption(0), "Both knees even");
});

test("shared axes cover empty, missing and larger peaks without classification cutoffs", () => {
  assert.equal(m.yMaxOf([null, NaN, Infinity]), 12);
  assert.equal(m.yMaxOf([]), 12);
  assert.equal(m.yMaxOf([3, 11]), 12);
  assert.equal(m.yMaxOf([13]), 18);
  assert.equal(m.yTicks(18).join(","), "0,9,18");
  assert.equal(m.scale(0, 2600, 0, 100)(1300), 50);
  assert.equal(m.scale(0, 0, 0, 100)(0), 0);
});

test("phase selection respects boundaries and does not guess missing phases", () => {
  const rep = fixture().reps[6];
  for (const [time, phase] of [[0, "descent"], [1205, "bottom"], [1595, "bottom"], [2200, "ascent"], [3000, "ascent"]]) {
    assert.equal(m.phaseAtTime(rep, time), phase);
  }
  assert.equal(m.phaseAtTime({ ...rep, phases: null }, 2200), null);
});

test("interpolation returns recorded peak, clamps endpoints and rejects corrupt series", () => {
  const { tMs, rightDeg } = fixture().reps[6].series;
  assert.equal(m.interpolate(tMs, rightDeg, 2200), 11);
  assert.equal(m.interpolate(tMs, rightDeg, 2100), 8);
  assert.equal(m.interpolate(tMs, rightDeg, -1), 1);
  assert.equal(m.interpolate(tMs, rightDeg, 3000), 9);
  assert.equal(m.interpolate([], [], 0), null);
  assert.equal(m.interpolate([0, 1], [1], 0), null);
  assert.equal(m.interpolate([0, 0], [1, 2], 0), null);
  assert.equal(m.interpolate([0, 1], [1, NaN], 0), null);
});

test("mirror transform changes horizontal coordinates only when capture was not mirrored", () => {
  assert.equal(m.mirrorX(0.25, true), 0.25);
  assert.equal(m.mirrorX(0.25, false), 0.75);
});

test("default selection excludes unassessable peaks and handles empty sets", () => {
  assert.equal(m.selectDefaultRep(fixture()).index, 7);
  assert.equal(m.selectDefaultRep(fixture("unassessable")).index, 8);
  assert.equal(m.selectDefaultRep(fixture("all_aligned")).index, 1);
  assert.equal(m.selectDefaultRep(fixture("zero_assessable")).index, 1);
  const empty = fixture();
  empty.reps = [];
  assert.equal(m.selectDefaultRep(empty), null);
});

test("insight uses the provided peak phase and refuses missing timing", () => {
  const rep = fixture().reps[6];
  assert.equal(m.selectInsight(rep), "Your right knee moved inward most during the ascent.");
  assert.equal(m.selectInsight({ ...rep, status: "borderline" }), "Your right knee drifted slightly inward during the ascent.");
  assert.equal(m.selectInsight({ ...rep, phases: null }), null);
  assert.equal(m.selectInsight(fixture().reps[0]), "Both knees stayed in line through this rep.");
});

test("unassessable reasons explain exclusions and never become praise", () => {
  const rep = fixture("unassessable").reps[6];
  assert.match(m.selectUnassessableCopy(rep).title, /knee left the frame/);
  for (const reason of ["knee_out_of_frame", "low_tracking_confidence", "rep_not_segmentable"]) {
    assert.match(m.selectUnassessableCopy({ ...rep, reason }).body, /left it out of your results/);
  }
  assert.equal(m.selectFocusCues(fixture("zero_assessable")).length, 0);
  assert.match(m.selectFocusCues(fixture("all_aligned"))[0], /Great alignment/);
});

test("status presentation keeps unavailable distinct and uses readable text colors", () => {
  assert.equal(m.STATUS.unassessable.dashed, true);
  assert.notEqual(m.STATUS.unassessable.text, m.STATUS.unassessable.fill);
  assert.equal(m.STATUS.deviated.icon, "arrowSW");
});

test("development validation rejects missing knees, inconsistent counts and excluded aggregates", () => {
  const main = fixture();
  main.reps[0].kneeStatus.left = "unassessable";
  assert.throws(() => m.assertSessionResult(main), /missing knee/);
  const counts = fixture();
  counts.summary.counts.aligned++;
  assert.throws(() => m.assertSessionResult(counts), /count mismatch/);
  const excluded = fixture("unassessable");
  excluded.summary.right.worstPeakDeg = 11;
  assert.throws(() => m.assertSessionResult(excluded), /aggregate/);
  const reversed = fixture();
  reversed.summary.balanceDeg = -8;
  assert.throws(() => m.assertSessionResult(reversed), /balance/);
});

function poseFrame(tMs) {
  return { tMs, pts: {
    nose: [0.5, 0.1], lShoulder: [0.35, 0.25], rShoulder: [0.65, 0.25],
    lHip: [0.4, 0.5], rHip: [0.6, 0.5], lKnee: [0.35, 0.7], rKnee: [0.65, 0.7],
    lAnkle: [0.3, 0.9], rAnkle: [0.7, 0.9],
  } };
}

test("nearest landmark frame uses time distance, with earlier frames breaking ties", () => {
  const rep = fixture().reps[6];
  rep.frames = [poseFrame(2600), poseFrame(2200), poseFrame(2000), poseFrame(1400), poseFrame(0)];
  assert.equal(m.nearestFrame(rep, 2200).tMs, 2200);
  assert.equal(m.nearestFrame(rep, 2100).tMs, 2000);
  assert.equal(m.nearestFrame(rep, 9000).tMs, 2600);
  assert.equal(m.nearestFrame(rep, null), null);
  assert.equal(m.nearestFrame({ ...rep, frames: null }, 2200), null);
});

test("skeleton projection preserves uniform scale, centers hips, and mirrors horizontally", () => {
  const frame = poseFrame(2200);
  const normal = m.projectSkeleton(frame, true);
  const mirrored = m.projectSkeleton(frame, false);
  assert.ok(Math.abs((normal.lHip[0] + normal.rHip[0]) / 2 - 120) < 1e-9);
  assert.ok(Math.abs((normal.lHip[1] + normal.rHip[1]) / 2 - 92) < 1e-9);
  assert.ok(Math.abs(normal.lAnkle[1] - normal.lShoulder[1] - 130) < 1e-9);
  const xFactor = (normal.rHip[0] - normal.lHip[0]) / (frame.pts.rHip[0] - frame.pts.lHip[0]);
  const yFactor = (normal.lAnkle[1] - normal.lShoulder[1]) / (frame.pts.lAnkle[1] - frame.pts.lShoulder[1]);
  assert.ok(Math.abs(xFactor - yFactor) < 1e-9);
  assert.ok(Math.abs(normal.lKnee[0] + mirrored.lKnee[0] - 240) < 1e-9);
  assert.equal(normal.lKnee[1], mirrored.lKnee[1]);
  assert.equal(frame.pts.lHip[0], 0.4);
});

test("incomplete, non-normalized, and degenerate skeleton frames remain unavailable", () => {
  assert.equal(m.projectSkeleton(null, true), null);
  const incomplete = poseFrame(0);
  delete incomplete.pts.nose;
  assert.equal(m.projectSkeleton(incomplete, true), null);
  const invalid = poseFrame(0);
  invalid.pts.lKnee[0] = 4;
  assert.equal(m.projectSkeleton(invalid, true), null);
  const flat = poseFrame(0);
  flat.pts.lAnkle[1] = flat.pts.rAnkle[1] = 0.25;
  assert.equal(m.projectSkeleton(flat, true), null);
});

test("live readouts interpolate stored series independently of landmark geometry", () => {
  const rep = fixture().reps[6];
  assert.equal(m.angleAtTime(rep, "right", 2200), 11);
  assert.equal(m.angleAtTime(rep, "right", 2100), 8);
  assert.equal(m.angleAtTime(rep, "left", 2100), 2.5);
  rep.frames = [poseFrame(2200)];
  rep.frames[0].pts.rKnee = [0.1, 0.1];
  assert.equal(m.angleAtTime(rep, "right", 2200), 11);
  assert.equal(m.angleAtTime({ ...rep, series: null }, "right", 2200), null);
  assert.equal(m.formatAngle(11), "11°");
  assert.equal(m.formatAngle(2.54), "2.5°");
  assert.equal(m.formatAngle(null), "—");
});

test("scrubber and chart share a time scale and clamp only the playhead domain", () => {
  const x = m.timeScale(2600, 280, 32);
  assert.equal(x(0), 32);
  assert.equal(x(2600), 248);
  assert.equal(m.timeFromPosition(140, 280, 2600, 32), 1300);
  assert.equal(m.timeFromPosition(-500, 280, 2600, 32), 0);
  assert.equal(m.timeFromPosition(9000, 280, 2600, 32), 2600);
  assert.equal(m.timeScale(null, 280, 32), null);
  assert.equal(m.timeScale(0, 280, 32), null);
  assert.equal(m.timeScale(2600, 64, 32), null);
});

test("line paths use recorded samples and interpolate exact off-track boundaries", () => {
  const { tMs, rightDeg } = fixture().reps[6].series;
  const identity = value => value;
  const clipped = m.seriesPath(tMs, rightDeg, identity, identity, { startMs: 2100, endMs: 2400 });
  assert.equal(clipped, "M2100.00 8.00 L2200.00 11.00 L2400.00 10.00");
  assert.equal(m.seriesPath(tMs, rightDeg, identity, identity, { startMs: 5000, endMs: 6000 }), "");
  assert.equal(m.seriesPath([0, 0], [1, 2], identity, identity), "");
  assert.equal(m.seriesPath([], [], identity, identity), "");
  assert.equal(m.seriesPath([0, 1], [1, NaN], identity, identity), "");
});

test("direct L/R end labels remain separated and within the plot", () => {
  for (const point of [0, 72, 144]) {
    const labels = m.lineLabelPositions(point, point, 144);
    assert.ok(Math.abs(labels.left - labels.right) >= 28);
    assert.ok(labels.left >= 0 && labels.right <= 144);
  }
});
