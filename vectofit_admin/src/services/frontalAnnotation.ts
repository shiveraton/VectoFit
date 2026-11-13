import type {
  AnnotationSession,
  DatasetSample,
} from "./datasetAnnotationService";

export function isFrontalAnnotationSample(sample: DatasetSample): boolean {
  if (sample.dataset_video !== null) {
    return (
      typeof sample.dataset_video === "object" &&
      sample.dataset_video.view_angle_name === "frontal"
    );
  }
  return sample.view_angle_name === "frontal";
}

export function frontalAnnotationSession(
  session: AnnotationSession,
): AnnotationSession {
  const samples = session.samples.filter(isFrontalAnnotationSample);
  return {
    ...session,
    excluded_view_sample_count:
      (session.excluded_view_sample_count ?? 0) +
      session.samples.length -
      samples.length,
    dataset: {
      ...session.dataset,
      sample_count: samples.length,
      labelled_sample_count: samples.filter(
        (sample) => sample.knee_annotation != null,
      ).length,
    },
    samples,
  };
}

export function annotationVideoUrl(
  sample: DatasetSample | null,
  datasetVideoUrl: string | null,
): string | null {
  if (!sample || !isFrontalAnnotationSample(sample)) return null;
  if (sample.dataset_video === null) return datasetVideoUrl;
  return typeof sample.dataset_video === "object"
    ? sample.dataset_video.video_url
    : null;
}
