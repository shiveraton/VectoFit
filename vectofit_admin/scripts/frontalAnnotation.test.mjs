import test from "node:test";
import assert from "node:assert/strict";
import { annotationVideoUrl, frontalAnnotationSession } from "../src/services/frontalAnnotation.ts";

const videoSample = (id, angle, videoUrl = `/videos/${id}`) => ({
    id, dataset_video: { id, view_angle_name: angle, video_url: videoUrl }, knee_annotation: null,
});
const session = samples => ({
    dataset: { id: 17, video_url: "/dataset-video", sample_count: samples.length, labelled_sample_count: 199 },
    samples,
});

test("mixed and cached sessions expose only explicitly frontal samples", () => {
    const source = session([
        videoSample(1, "diagonal"),
        { ...videoSample(2, "frontal"), knee_annotation: { notes: "existing rating" } },
        videoSample(3, "sagittal"),
        videoSample(4, "unknown"),
        { id: 5, dataset_video: null, view_angle_name: "frontal" },
        { id: 6, dataset_video: null },
        { id: 7, dataset_video: 7, view_angle_name: "frontal" },
        { ...videoSample(8, "diagonal"), view_angle_name: "frontal" },
    ]);
    const original = structuredClone(source);
    const result = frontalAnnotationSession(source);
    assert.deepEqual(result.samples.map(sample => sample.id), [2, 5]);
    assert.equal(result.excluded_view_sample_count, 6);
    assert.equal(result.dataset.sample_count, 2);
    assert.equal(result.dataset.labelled_sample_count, 1);
    assert.deepEqual(source, original);
    assert.deepEqual(frontalAnnotationSession(result), result);
});

test("an excluded-only response produces an empty annotation queue", () => {
    const result = frontalAnnotationSession(session([videoSample(1, "diagonal"), videoSample(2, "sagittal")]));
    assert.deepEqual(result.samples, []);
    assert.equal(result.dataset.sample_count, 0);
    assert.equal(result.dataset.labelled_sample_count, 0);
});

test("non-frontal samples cannot select a playback URL", () => {
    for (const angle of ["diagonal", "sagittal", undefined]) {
        assert.equal(annotationVideoUrl(videoSample(1, angle), "/dataset-video"), null);
    }
    assert.equal(annotationVideoUrl(null, "/dataset-video"), null);
});

test("missing per-video media never falls back to a different dataset video", () => {
    assert.equal(annotationVideoUrl(videoSample(1, "frontal", null), "/wrong-video"), null);
    assert.equal(annotationVideoUrl(videoSample(1, "frontal"), "/wrong-video"), "/videos/1");
});

test("legacy dataset playback requires an explicit frontal angle", () => {
    assert.equal(annotationVideoUrl({ id: 1, dataset_video: null, view_angle_name: "frontal" }, "/legacy-video"), "/legacy-video");
    assert.equal(annotationVideoUrl({ id: 1, dataset_video: null }, "/legacy-video"), null);
});
