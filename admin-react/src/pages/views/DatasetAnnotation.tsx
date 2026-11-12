import { useState, useRef } from "react";
import { useEffect } from "react";
import type { ChangeEvent } from "react";
import { useNavigate, useParams } from "react-router";
import { useDatasetAnnotation } from "../../hooks/useDatasetAnnotation";
import type {
  KneeAlignmentGrade,
  KneeDeviationDirection,
  SymmetryObservation,
} from "../../services/datasetAnnotationService";
import { bindStyles, each, display, scopeAttributes } from "../../presentation";
import styles from "./DatasetAnnotation.module.css";
import { annotationVideoUrl } from "../../services/frontalAnnotation";
import SquatReferenceModal from "../../components/datasets/SquatReferenceModal";

export default function DatasetAnnotation(input: {}) {
  const cx = bindStyles(styles);
  const params = useParams();
  const navigate = useNavigate();
  const route = { params };
  const router = { push: navigate };
  const datasetHome =
    import.meta.env.MODE === "public" ? "/annotator" : "/dataset";
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [referenceOpen, setReferenceOpen] = useState(false);
  const [videoError, setVideoError] = useState("");
  const [reviewingCompleted, setReviewingCompleted] = useState(false);
  const kneeSides = ["left", "right"] as const;
  const kneeGrades: KneeAlignmentGrade[] = [
    "aligned",
    "borderline",
    "deviated",
    "unassessable",
  ];
  function handleDirectionChange(
    side: "left" | "right",
    event: ChangeEvent<HTMLSelectElement>,
  ) {
    setKneeDirection(
      side,
      (event.target as HTMLSelectElement).value as KneeDeviationDirection,
    );
  }
  function handleSymmetryChange(event: ChangeEvent<HTMLSelectElement>) {
    setSymmetryObservation(
      (event.target as HTMLSelectElement).value as SymmetryObservation,
    );
  }
  function handleNotesInput(event: ChangeEvent<HTMLTextAreaElement>) {
    setNotes((event.target as HTMLTextAreaElement).value);
  }
  const {
    session,
    samples,
    currentSample,
    currentIndex,
    fps,
    annotation,
    targetLabel,
    labelledCount,
    pendingReviewCount,
    isReviewComplete,
    currentSampleLabelState,
    isLoading,
    isSaving,
    error,
    setKneeGrade,
    setKneeDirection,
    setSymmetryObservation,
    setNotes,
    saveAndNext,
    clear,
    previous,
    next,
  } = useDatasetAnnotation(Number(params.id));
  const activeVideo = (() => {
    const video = currentSample?.dataset_video;
    return video && typeof video === "object" ? video : null;
  })();
  const activeVideoUrl = annotationVideoUrl(
    currentSample,
    session?.dataset.video_url ?? null,
  );
  const activeVideoLabel = (() => {
    const video = activeVideo;
    if (!video) {
      return "Dataset-level video";
    }
    if (import.meta.env.MODE === "public") {
      return [video.participant_code, video.view_angle_name]
        .filter(Boolean)
        .join(" / ");
    }
    const sourceLabel =
      video.source_label === true
        ? "GOOD FORM"
        : video.source_label === false
          ? "BAD FORM"
          : "UNKNOWN LABEL";
    return [
      video.participant_code ? `Participant ${video.participant_code}` : null,
      video.view_angle_name,
      `${sourceLabel}`,
    ]
      .filter(Boolean)
      .join(" · ");
  })();
  const currentFps = (() => {
    const sampleFps = currentSample?.video_fps;
    return sampleFps != null && sampleFps > 0 ? sampleFps : fps;
  })();
  const repStartTime = (() => {
    const startFrame = currentSample?.rep_assessment.start_frame;
    if (startFrame == null || currentFps <= 0) {
      return 0;
    }
    return startFrame / currentFps;
  })();
  const repEndTime = (() => {
    const endFrame = currentSample?.rep_assessment.end_frame;
    if (endFrame == null || currentFps <= 0) {
      return null;
    }
    return endFrame / currentFps;
  })();
  function seekToRep() {
    const video = videoRef.current;
    if (!video || video.readyState < HTMLMediaElement.HAVE_METADATA) {
      return;
    }
    video.currentTime = repStartTime;
  }
  function handleVideoLoadedMetadata() {
    const video = videoRef.current;
    if (!video) return;
    setVideoError("");
    video.playbackRate = playbackRate;
    seekToRep();
  }
  function handleTimeUpdate() {
    const video = videoRef.current;
    if (!video || repEndTime == null || video.currentTime < repEndTime) {
      return;
    }
    video.pause();
    seekToRep();
  }
  async function playRep() {
    const video = videoRef.current;
    if (!video || !activeVideoUrl) {
      return;
    }
    setVideoError("");
    if (video.readyState < HTMLMediaElement.HAVE_METADATA) {
      setVideoError("The source video is still loading.");
      return;
    }
    video.playbackRate = playbackRate;
    seekToRep();
    try {
      await video.play();
    } catch (playError) {
      console.error("Could not play the current repetition.", playError);
      setVideoError("Could not play this video. Please try again.");
    }
  }
  useEffect(() => {
    videoRef.current?.pause();
    setVideoError("");
    const frame = requestAnimationFrame(seekToRep);
    return () => cancelAnimationFrame(frame);
  }, [currentSample?.id, activeVideoUrl, repStartTime]);
  useEffect(() => {
    if (videoRef.current) videoRef.current.playbackRate = playbackRate;
  }, [playbackRate]);
  const handleSaveNext = async () => {
    await saveAndNext();
  };
  useEffect(() => {
    const id = Number(route.params.id);
    if (!Number.isInteger(id) || id <= 0) void navigate(datasetHome);
  }, [params.id, navigate]);
  return (
    <>
      <div
        {...scopeAttributes(input)}
        data-v-dataset-annotation=""
        className={cx("annotation-page")}
      >
        <header data-v-dataset-annotation="" className={cx("page-header")}>
          <div data-v-dataset-annotation="">
            <div data-v-dataset-annotation="" className={cx("eyebrow")}>
              {"DATASET ANNOTATION"}
            </div>
            <h1 data-v-dataset-annotation="">
              {display(session?.dataset.name)}
            </h1>
            <p data-v-dataset-annotation="">
              {"Frontal knee-alignment annotation"}
            </p>
          </div>
          <button
            data-v-dataset-annotation=""
            type="button"
            disabled={isSaving}
            onClick={() => {
              router.push(datasetHome);
            }}
            className={cx("secondary-button")}
          >
            {" Back to Datasets "}
          </button>
        </header>
        {isLoading ? (
          <div
            data-v-dataset-annotation=""
            role="status"
            className={cx("loading")}
          >
            {"Loading annotation workspace..."}
          </div>
        ) : null}
        {error ? (
          <div
            data-v-dataset-annotation=""
            role="alert"
            className={cx("error")}
          >
            {display(error)}
          </div>
        ) : null}
        {!isLoading && (session?.excluded_view_sample_count ?? 0) > 0 ? (
          <p role="status">
            {session?.excluded_view_sample_count} repetitions excluded because
            their camera view is not frontal or is unknown.
          </p>
        ) : null}
        {!isLoading && session && samples.length === 0 ? (
          <section
            data-v-dataset-annotation=""
            className={cx("annotation-card annotation-empty")}
          >
            <h2>No eligible frontal repetitions</h2>
            <p>
              Diagonal, sagittal and unknown-angle samples are excluded from
              knee annotation.
            </p>
          </section>
        ) : null}
        {!isLoading &&
        session &&
        samples.length > 0 &&
        isReviewComplete &&
        !reviewingCompleted ? (
          <section
            data-v-dataset-annotation=""
            className={cx("annotation-card annotation-complete")}
          >
            <h2 data-v-dataset-annotation="">{"Manual Review Complete"}</h2>
            <p data-v-dataset-annotation="">
              {"All samples in this review queue have been manually annotated."}
            </p>
            <div
              data-v-dataset-annotation=""
              className={cx("completion-count")}
            >
              <strong data-v-dataset-annotation="">
                {display(labelledCount)}
                {" / "}
                {display(samples.length)}
              </strong>
              <span data-v-dataset-annotation="">{"Samples reviewed"}</span>
            </div>
            <p data-v-dataset-annotation="" className={cx("completion-note")}>
              {" All of your ratings have been saved and confirmed. "}
            </p>
            <button
              data-v-dataset-annotation=""
              type="button"
              onClick={() => {
                router.push(datasetHome);
              }}
              className={cx("primary-button")}
            >
              {" Return to Datasets "}
            </button>
            <button
              data-v-dataset-annotation=""
              type="button"
              onClick={() => {
                setReviewingCompleted(true);
              }}
              className={cx("secondary-button")}
            >
              {" Review saved ratings "}
            </button>
          </section>
        ) : !isLoading && session && currentSample ? (
          <>
            <section
              data-v-dataset-annotation=""
              className={cx("annotation-card annotation-meta")}
            >
              <div data-v-dataset-annotation="">
                <span data-v-dataset-annotation="">{"Progress"}</span>
                <strong data-v-dataset-annotation="">
                  {display(currentIndex + 1)}
                  {" / "}
                  {display(samples.length)}
                </strong>
              </div>
              <div data-v-dataset-annotation="">
                <span data-v-dataset-annotation="">{"Manually Reviewed"}</span>
                <strong data-v-dataset-annotation="">
                  {display(labelledCount)}
                  {" / "}
                  {display(samples.length)}
                </strong>
              </div>
              <div data-v-dataset-annotation="">
                <span data-v-dataset-annotation="">{"Awaiting Review"}</span>
                <strong data-v-dataset-annotation="">
                  {display(pendingReviewCount)}
                </strong>
              </div>
            </section>
            <div
              data-v-dataset-annotation=""
              className={cx("annotation-workspace")}
            >
              <section
                data-v-dataset-annotation=""
                className={cx("annotation-card video-panel")}
              >
                <div
                  data-v-dataset-annotation=""
                  className={cx("video-source-meta")}
                >
                  <span data-v-dataset-annotation="">{"Current video: "}</span>
                  <strong data-v-dataset-annotation="">
                    {display(activeVideoLabel)}
                  </strong>
                </div>
                {activeVideoUrl ? (
                  <video
                    data-v-dataset-annotation=""
                    key={activeVideoUrl}
                    ref={videoRef}
                    src={activeVideoUrl}
                    controls
                    playsInline
                    preload="metadata"
                    onError={() =>
                      setVideoError(
                        "Unable to load this video. Retry, or return to the dataset list.",
                      )
                    }
                    onLoadedMetadata={handleVideoLoadedMetadata}
                    onTimeUpdate={handleTimeUpdate}
                  ></video>
                ) : (
                  <div
                    data-v-dataset-annotation=""
                    className={cx("video-unavailable")}
                  >
                    <strong data-v-dataset-annotation="">
                      {"Source video unavailable"}
                    </strong>
                    <p data-v-dataset-annotation="">
                      {
                        " This repetition does not have a playable video URL. Check the imported video's processing status. "
                      }
                    </p>
                  </div>
                )}
                {videoError ? (
                  <p
                    data-v-dataset-annotation=""
                    className={cx("video-error")}
                    role="alert"
                  >
                    {display(videoError)}
                  </p>
                ) : null}
                <div
                  data-v-dataset-annotation=""
                  className={cx("video-controls")}
                >
                  <button
                    data-v-dataset-annotation=""
                    type="button"
                    disabled={isSaving || currentIndex === 0}
                    onClick={() => previous()}
                  >
                    {" Previous "}
                  </button>
                  {videoError && activeVideoUrl && (
                    <button
                      type="button"
                      onClick={() => {
                        setVideoError("");
                        videoRef.current?.load();
                      }}
                    >
                      Retry video
                    </button>
                  )}
                  <button
                    data-v-dataset-annotation=""
                    type="button"
                    disabled={!activeVideoUrl}
                    onClick={() => playRep()}
                  >
                    {" Play Rep "}
                  </button>
                  <button
                    data-v-dataset-annotation=""
                    type="button"
                    disabled={isSaving || currentIndex >= samples.length - 1}
                    onClick={() => next()}
                  >
                    {" Next "}
                  </button>
                  <select
                    data-v-dataset-annotation=""
                    value={playbackRate ?? ""}
                    onChange={(event) =>
                      setPlaybackRate(Number(event.target.value))
                    }
                    aria-label="Playback speed"
                  >
                    <option data-v-dataset-annotation="" value={0.5}>
                      {"0.5×"}
                    </option>
                    <option data-v-dataset-annotation="" value={0.75}>
                      {"0.75×"}
                    </option>
                    <option data-v-dataset-annotation="" value={1}>
                      {"1×"}
                    </option>
                    <option data-v-dataset-annotation="" value={1.5}>
                      {"1.5×"}
                    </option>
                    <option data-v-dataset-annotation="" value={2}>
                      {"2×"}
                    </option>
                  </select>
                </div>
              </section>
              <section
                data-v-dataset-annotation=""
                className={cx("annotation-card criteria-panel")}
              >
                <fieldset
                  data-v-dataset-annotation=""
                  disabled={isSaving}
                  aria-label="Knee assessment"
                  className={cx("annotation-fields")}
                >
                  <div
                    data-v-dataset-annotation=""
                    className={cx("panel-heading")}
                  >
                    <div data-v-dataset-annotation="">
                      <span data-v-dataset-annotation="">
                        {"Rep "}
                        {display(currentSample.rep_assessment.rep_number)}
                      </span>
                      <h2 data-v-dataset-annotation="">{"Knee Alignment"}</h2>
                      <button
                        type="button"
                        className={cx("reference-button")}
                        aria-haspopup="dialog"
                        onClick={() => {
                          videoRef.current?.pause();
                          setReferenceOpen(true);
                        }}
                      >
                        View reference
                      </button>
                      {currentSampleLabelState ? (
                        <p
                          data-v-dataset-annotation=""
                          className={cx(
                            "annotation-state",
                            `state-${currentSampleLabelState}`,
                          )}
                        >
                          {display(
                            currentSampleLabelState === "manual"
                              ? "Manually reviewed"
                              : currentSampleLabelState === "inherited"
                                ? "Inherited ZIP label — review needed"
                                : "Unreviewed",
                          )}
                        </p>
                      ) : null}
                    </div>
                    <span
                      data-v-dataset-annotation=""
                      className={cx([
                        "verdict",
                        (targetLabel ?? "pending").toLowerCase(),
                      ])}
                    >
                      {display(targetLabel?.toUpperCase() ?? "PENDING")}
                    </span>
                  </div>
                  <div
                    data-v-dataset-annotation=""
                    className={cx("criteria-list")}
                  >
                    {each(kneeSides).map(([_index, side]) => (
                      <div
                        data-v-dataset-annotation=""
                        key={side}
                        className={cx("criterion")}
                      >
                        <strong data-v-dataset-annotation="">
                          {display(
                            side === "left" ? "Left knee" : "Right knee",
                          )}
                        </strong>
                        <div
                          data-v-dataset-annotation=""
                          className={cx("criterion-actions")}
                        >
                          {each(kneeGrades).map(([_index, grade]) => (
                            <button
                              data-v-dataset-annotation=""
                              key={grade}
                              type="button"
                              aria-pressed={annotation[side].grade === grade}
                              aria-label={`${side} knee: ${grade}`}
                              onClick={() => {
                                setKneeGrade(side, grade);
                              }}
                              className={cx({
                                active: annotation[side].grade === grade,
                              })}
                            >
                              {display(grade)}
                            </button>
                          ))}
                        </div>
                        <select
                          data-v-dataset-annotation=""
                          aria-label={`${side} knee deviation direction`}
                          value={annotation[side].direction ?? ""}
                          disabled={
                            annotation[side].grade === null ||
                            annotation[side].grade === "unassessable" ||
                            annotation[side].grade === "aligned"
                          }
                          onChange={(event) => {
                            handleDirectionChange(side, event);
                          }}
                        >
                          <option
                            data-v-dataset-annotation=""
                            value="uncertain"
                          >
                            {"Direction uncertain"}
                          </option>
                          <option data-v-dataset-annotation="" value="valgus">
                            {"Valgus (inward)"}
                          </option>
                          <option data-v-dataset-annotation="" value="varus">
                            {"Varus (outward)"}
                          </option>
                        </select>
                      </div>
                    ))}
                  </div>
                  <label
                    data-v-dataset-annotation=""
                    className={cx("error-label-field")}
                  >
                    <span data-v-dataset-annotation="">
                      {"Symmetry observation"}
                    </span>
                    <select
                      data-v-dataset-annotation=""
                      value={annotation.symmetry_observation}
                      onChange={handleSymmetryChange}
                    >
                      <option data-v-dataset-annotation="" value="not_recorded">
                        {"Not recorded"}
                      </option>
                      <option data-v-dataset-annotation="" value="symmetric">
                        {"Symmetric"}
                      </option>
                      <option data-v-dataset-annotation="" value="asymmetric">
                        {"Asymmetric"}
                      </option>
                      <option data-v-dataset-annotation="" value="uncertain">
                        {"Uncertain"}
                      </option>
                    </select>
                  </label>
                  <label
                    data-v-dataset-annotation=""
                    className={cx("error-label-field")}
                  >
                    <span data-v-dataset-annotation="">{"Notes"}</span>
                    <textarea
                      data-v-dataset-annotation=""
                      value={annotation.notes}
                      rows={3}
                      onChange={handleNotesInput}
                    ></textarea>
                  </label>
                  <div
                    data-v-dataset-annotation=""
                    className={cx("annotation-actions")}
                  >
                    <button
                      data-v-dataset-annotation=""
                      type="button"
                      disabled={isSaving}
                      onClick={() => clear()}
                      className={cx("secondary-button")}
                    >
                      {" Clear "}
                    </button>
                    <button
                      data-v-dataset-annotation=""
                      type="button"
                      disabled={isSaving || targetLabel === null}
                      onClick={() => handleSaveNext()}
                      className={cx("primary-button")}
                    >
                      {display(isSaving ? "Saving..." : "Save & Next")}
                    </button>
                  </div>
                </fieldset>
              </section>
            </div>
          </>
        ) : null}
      </div>
      {referenceOpen && (
        <SquatReferenceModal onClose={() => setReferenceOpen(false)} />
      )}
    </>
  );
}
