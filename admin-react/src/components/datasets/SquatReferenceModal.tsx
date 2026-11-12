import { useEffect, useRef, useState } from "react";
import styles from "./SquatReferenceModal.module.css";

const grades = [
  ["Aligned", "No clear inward or outward knee deviation is visible."],
  [
    "Borderline",
    "Alignment is near the boundary between aligned and deviated.",
  ],
  ["Deviated", "Clear inward or outward knee deviation is visible."],
  ["Unassessable", "Visibility or video quality prevents a reliable judgment."],
];

export default function SquatReferenceModal({
  onClose,
}: {
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoError, setVideoError] = useState(false);
  const [autoplay] = useState(
    () => !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );

  useEffect(() => {
    const previousFocus = document.activeElement;
    const dialog = dialogRef.current;
    const video = videoRef.current;
    const previousOverflow = document.body.style.overflow;
    dialog?.showModal();
    document.body.style.overflow = "hidden";
    return () => {
      video?.pause();
      dialog?.close();
      document.body.style.overflow = previousOverflow;
      if (previousFocus instanceof HTMLElement) previousFocus.focus();
    };
  }, []);

  return (
    <dialog
      ref={dialogRef}
      className={styles.dialog}
      aria-labelledby="squat-reference-title"
      onCancel={onClose}
    >
      <header className={styles.header}>
        <div>
          <h2 id="squat-reference-title">Squat reference</h2>
          <p>Bodyweight squat ? Frontal view</p>
        </div>
        <button type="button" onClick={onClose} autoFocus>
          Close
        </button>
      </header>
      <div className={styles.content}>
        <section aria-label="Reference video">
          <video
            ref={videoRef}
            className={styles.video}
            src={`${import.meta.env.BASE_URL}videos/squat_ref-front.mp4`}
            aria-label="Frontal-view bodyweight squat reference"
            autoPlay={autoplay}
            muted
            loop
            playsInline
            controls
            preload="auto"
            onError={() => setVideoError(true)}
          />
          {videoError ? (
            <p role="alert">
              The reference video could not load. Close and reopen the reference
              to retry.
            </p>
          ) : (
            <div className={styles.playback}>
              <span>
                {autoplay
                  ? "Loops automatically. Use the video controls to pause or play."
                  : "Use Play to start the reference. Reduced motion is enabled."}
              </span>
              <button
                type="button"
                onClick={() => {
                  if (videoRef.current) videoRef.current.currentTime = 0;
                }}
              >
                Restart
              </button>
            </div>
          )}
          <aside className={styles.reminder}>
            <strong>Reference only</strong>
            <p>
              This video demonstrates a reference bodyweight squat from the
              frontal view. Body proportions and movement styles vary; imitation
              does not guarantee ideal execution. Judge the visible repetition
              using the annotation criteria. Annotate thoughtfully.
            </p>
          </aside>
        </section>
        <section
          className={styles.guide}
          aria-labelledby="reference-label-guide"
        >
          <h3 id="reference-label-guide">Annotation guide</h3>
          <p>
            Assess each knee separately using the study criteria. This reference
            supports knee-alignment annotation, not an assessment of every
            aspect of squat form.
          </p>
          <dl>
            {grades.map(([label, description]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{description}</dd>
              </div>
            ))}
          </dl>
          <h3>Deviation direction</h3>
          <p>
            <strong>Valgus:</strong> inward. <strong>Varus:</strong> outward.
            Choose <strong>Direction uncertain</strong> when the direction
            cannot be judged reliably.
          </p>
          <h3>Symmetry observation</h3>
          <p>
            <strong>Symmetric:</strong> similar visible movement on both sides.{" "}
            <strong>Asymmetric:</strong> a visible difference between sides.{" "}
            <strong>Uncertain:</strong> cannot judge reliably.{" "}
            <strong>Not recorded:</strong> no symmetry observation entered.
          </p>
        </section>
      </div>
    </dialog>
  );
}
