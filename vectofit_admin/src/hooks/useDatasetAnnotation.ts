import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  datasetAnnotationService,
  annotationRequestError,
  emptyKneeAnnotation,
  type AnnotationSession,
  type DatasetSample,
  type KneeAnnotation,
  type KneeAlignmentGrade,
  type KneeDeviationDirection,
  type TargetLabel,
} from "../services/datasetAnnotationService";
import { queryKeys } from "../query";
import { frontalAnnotationSession } from "../services/frontalAnnotation";

const clone = (value: KneeAnnotation): KneeAnnotation => structuredClone(value);
export function deriveTargetLabel(
  annotation: KneeAnnotation,
): TargetLabel | null {
  const left = annotation.left.grade,
    right = annotation.right.grade;
  if (left === null || right === null) return null;
  if (left === "deviated" || right === "deviated") return "bad";
  if (left === "unassessable" || right === "unassessable")
    return "unassessable";
  if (left === "borderline" || right === "borderline") return "borderline";
  return "good";
}
export function mergeSavedSample(
  original: DatasetSample,
  saved: DatasetSample,
): DatasetSample {
  return {
    ...original,
    ...saved,
    dataset_video:
      saved.dataset_video !== null && typeof saved.dataset_video === "object"
        ? saved.dataset_video
        : original.dataset_video,
    video_fps: saved.video_fps ?? original.video_fps ?? null,
  };
}
export function useDatasetAnnotation(datasetId: number) {
  const cache = useQueryClient();
  const lock = useRef(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [annotation, setAnnotation] =
    useState<KneeAnnotation>(emptyKneeAnnotation);
  const [error, setError] = useState<string | null>(null);
  const query = useQuery({
    queryKey: queryKeys.annotation(datasetId),
    queryFn: () => datasetAnnotationService.getSession(datasetId),
    select: frontalAnnotationSession,
    enabled: Number.isInteger(datasetId) && datasetId > 0,
    refetchOnMount: "always",
  });
  const initialSession = useRef<AnnotationSession | null>(null);
  const session = query.data ?? null,
    samples = session?.samples ?? [];
  const currentSample = samples[currentIndex] ?? null;
  useEffect(() => {
    setCurrentIndex((index) =>
      Math.min(index, Math.max(0, samples.length - 1)),
    );
  }, [samples.length]);
  useEffect(() => {
    initialSession.current = null;
    setCurrentIndex(0);
    setAnnotation(emptyKneeAnnotation());
    setError(null);
  }, [datasetId]);
  useEffect(() => {
    if (query.data && !query.isFetching && initialSession.current === null) {
      initialSession.current = query.data;
      setCurrentIndex(
        Math.max(
          0,
          query.data.samples.findIndex(
            (sample) => sample.knee_annotation == null,
          ),
        ),
      );
    }
  }, [query.data, query.isFetching]);
  useEffect(() => {
    setAnnotation(
      currentSample?.knee_annotation
        ? clone(currentSample.knee_annotation)
        : emptyKneeAnnotation(),
    );
  }, [currentSample?.id]);
  const targetLabel = deriveTargetLabel(annotation);
  const labelledCount = samples.filter(
    (sample) => sample.knee_annotation != null,
  ).length;
  const pendingReviewCount = samples.length - labelledCount;
  const isReviewComplete = samples.length > 0 && pendingReviewCount === 0;
  const saveRequest = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: KneeAnnotation }) =>
      datasetAnnotationService.save(id, { knee_annotation: payload }),
  });
  const clearRequest = useMutation({
    mutationFn: datasetAnnotationService.clear,
  });
  const isSaving = saveRequest.isPending || clearRequest.isPending;
  function updateSample(original: DatasetSample, saved: DatasetSample) {
    const updated = mergeSavedSample(original, saved);
    cache.setQueryData<AnnotationSession>(
      queryKeys.annotation(datasetId),
      (previous) =>
        previous
          ? {
              ...previous,
              samples: previous.samples.map((sample) =>
                sample.id === original.id ? updated : sample,
              ),
            }
          : previous,
    );
    void cache.invalidateQueries({ queryKey: queryKeys.datasets });
    void cache.invalidateQueries({ queryKey: queryKeys.annotationPool });
    return updated;
  }
  async function saveAndNext() {
    if (lock.current) return false;
    if (!currentSample || targetLabel === null) {
      setError("Assess both knees before saving.");
      return false;
    }
    lock.current = true;
    setError(null);
    try {
      const payload = clone(annotation);
      const saved = await saveRequest.mutateAsync({
        id: currentSample.id,
        payload,
      });
      const updated = updateSample(currentSample, {
        ...saved,
        knee_annotation: saved.knee_annotation ?? payload,
        target_label: saved.target_label ?? targetLabel,
      });
      const nextSamples = samples.map((sample) =>
        sample.id === updated.id ? updated : sample,
      );
      const later = nextSamples.findIndex(
        (sample, index) =>
          index > currentIndex && sample.knee_annotation == null,
      );
      const next =
        later >= 0
          ? later
          : nextSamples.findIndex((sample) => sample.knee_annotation == null);
      if (next >= 0) {
        setCurrentIndex(next);
        setAnnotation(
          nextSamples[next].knee_annotation
            ? clone(nextSamples[next].knee_annotation!)
            : emptyKneeAnnotation(),
        );
      }
      return true;
    } catch (error) {
      setError(annotationRequestError(error, "Failed to save knee annotation."));
      return false;
    } finally {
      lock.current = false;
    }
  }
  async function clear() {
    if (!currentSample || lock.current) return;
    lock.current = true;
    setError(null);
    try {
      const saved = await clearRequest.mutateAsync(currentSample.id);
      updateSample(currentSample, {
        ...saved,
        knee_annotation: null,
        target_label: null,
      });
      setAnnotation(emptyKneeAnnotation());
    } catch (error) {
      setError(annotationRequestError(error, "Failed to clear knee annotation."));
    } finally {
      lock.current = false;
    }
  }
  return {
    session,
    samples,
    currentSample,
    currentIndex,
    fps: session?.fps ?? 0,
    annotation,
    targetLabel,
    labelledCount,
    pendingReviewCount,
    isReviewComplete,
    inheritedLabelCount: samples.filter(
      (sample) => sample.knee_annotation == null && sample.is_correct != null,
    ).length,
    currentSampleLabelState: currentSample
      ? currentSample.knee_annotation != null
        ? "manual"
        : currentSample.is_correct != null
          ? "inherited"
          : "unlabeled"
      : null,
    isLoading: query.isFetching,
    isSaving,
    error: error || (query.error ? "Unable to load annotation data." : null),
    setKneeGrade: (side: "left" | "right", grade: KneeAlignmentGrade | null) =>
      setAnnotation((previous) => {
        let direction = previous[side].direction;
        if (grade === null || grade === "unassessable") direction = null;
        else if (grade === "aligned") direction = "none";
        else if (direction === null || direction === "none")
          direction = "uncertain";
        return { ...previous, [side]: { grade, direction } };
      }),
    setKneeDirection: (
      side: "left" | "right",
      direction: KneeDeviationDirection,
    ) =>
      setAnnotation((previous) => ({
        ...previous,
        [side]: { ...previous[side], direction },
      })),
    setNotes: (value: string) =>
      setAnnotation((previous) => ({ ...previous, notes: value })),
    saveAndNext,
    clear,
    previous: () => {
      if (!lock.current && currentIndex > 0) setCurrentIndex(currentIndex - 1);
    },
    next: () => {
      if (!lock.current && currentIndex < samples.length - 1)
        setCurrentIndex(currentIndex + 1);
    },
  };
}
