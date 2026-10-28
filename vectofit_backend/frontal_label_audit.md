# Frontal knee alignment label audit

## Scope and evidence

This audit distinguishes the intended prediction target from the labels currently represented in the code. It is based on the repository implementation and checked-in annotation audit artifact. The live audit script (`run_frontal_audit.py`, dataset ID 17) could not connect to its configured Supabase PostgreSQL database in this environment, so current dataset-17 sample counts, per-participant counts, and source/current label agreement remain unverified. The reported five-participant composition and P04's single Bad repetition are treated as supplied dataset facts, not independently confirmed here.

## Target label semantics

For a **knee-alignment-only** classifier, define the unit as one complete squat repetition, with both knees judged through the repetition from a usable frontal view:

- **Good alignment:** neither knee shows clinically/visually meaningful medial collapse (dynamic knee valgus) nor excessive lateral bowing (varus) through the loaded squat phase, using a written, fixed visual rubric and sufficient visibility of hips, knees, and ankles.
- **Bad alignment:** at least one knee shows the defined valgus or varus fault during the loaded phase. Record the specific side and fault when possible. A repetition with an unobservable knee is **unassessable**, not Good.
- Depth, trunk lean, symmetry unrelated to frontal knee tracking, foot stability, and completion are not knee-alignment criteria. They must not turn an alignment-Good repetition into Bad for this target.

FPPA (frontal plane projection angle) is an image-plane proxy, not a direct 3-D anatomical measurement. If FPPA is the operational rule, document the exact landmarks, phase/frame selection, sign convention, aggregation across frames and sides, cutoffs, and treatment of poor pose visibility before labeling. The current inspected feature pipeline does not calculate FPPA: `features.py` extracts sagittal hip/knee angles, ROM, bilateral knee-angle asymmetry, trunk angle, and hip velocity. `classifier.py:evaluate_knee` accepts an already computed `knee["frontal"]` value and externally supplied `t["frontal"]` range; it maps below-range to `knee_varus` and above-range to `knee_valgus`. The inspected repository does not establish that value's FPPA formula, threshold values, image orientation/sign calibration, or provenance. Thus the mapping is an algorithmic rule conditional on upstream values, not evidence of human ground truth.

Use **valgus** for medial/inward knee deviation relative to the hip-to-foot line and **varus** for lateral/outward deviation. The code's low/high mapping is only correct if its upstream angle convention and threshold orientation encode these meanings; verify that convention against labeled frames before relying on it. A semantic label such as `knee_valgus` is a category value and must not be conflated with a measured FPPA threshold result.

## What the existing labels mean

The import code parses Good/Bad tokens from archive paths and writes them to `DatasetVideo.source_label`. Repetition creation copies that value into `DatasetSample.is_correct`. These operations do not inspect movement or identify a biomechanical criterion. Therefore, the source-folder labels are **inherited clip-level labels of undocumented rubric**, not verified knee-alignment ground truth. The path parser can establish where the class token was found; it cannot establish what the person who organized the source meant by Good or Bad.

The annotation UI defines a separate, broader manual rubric: depth, knee, trunk, symmetry, foot, and completion. Its verdict is Incorrect if any criterion fails and Correct only if all pass. Its suggested `knee_valgus` label is generated from the failed Knee criterion, while annotators can edit the error-label string. This is an overall squat-quality label, not knee-alignment-only. The checked-in annotation audit JSON records human actions and (in later records) per-criterion judgments for dataset 7. It does not establish the rubric behind dataset 17's source-folder labels.

The database fields further separate these concepts: `source_label` is described as inherited from a folder; `is_correct` as a coarse ground-truth label; `error_label` as optional semantic error class; and annotator/time identify some manual edits. Existing importer/repetition code does not persist a distinct origin or immutable source snapshot on each sample. A populated error label alone cannot prove whether it was a human annotation, a rule output, or copied/generated elsewhere. For dataset 17, that provenance needs verification from its sample audit trail and original annotation process; do not infer it from the string.

## Eligibility and relabel protocol

For the knee-alignment target, **do not train on inherited source Good/Bad labels or the broad six-criterion verdict as if they were knee-alignment ground truth**. Include only frontal repetitions with visible, assessable bilateral tracking and a criterion-specific human knee-alignment judgment. Prefer two independent reviewers, blinded to model predictions and source-folder labels, then adjudicate disagreements. Store a separate target label (`alignment_good`, `alignment_bad`, or `unassessable`), fault subtype/side, reviewer IDs, timestamp, rubric version, and adjudication note. Preserve `source_label`, existing `is_correct`, and `error_label` as untouched historical fields; record the new decisions in an append-only audit artifact/table keyed by stable sample ID. Exclude unassessable, ambiguous, missing-view, and provenance-unknown samples from the primary target dataset. FPPA may be retained as a separate measured feature/result with its own formula/version and thresholds; do not auto-convert it into human ground truth unless the study explicitly defines and validates a threshold-derived target.

If reannotation is not available, the defensible choice is to **filter out** samples without documented knee-specific labels and report that no adequate labeled set exists, rather than reinterpret the inherited folders. If the target is instead overall squat quality, state that explicitly and use the six-criterion rubric; it is a different task.

## Participant-level evaluation feasibility

The training loader groups by participant and `group_split` requires every target class in at least two distinct participants, then places whole participant groups in train or test. With five participants and P04's single Bad example, a participant holdout can be highly sensitive to that one repetition; if P04 is the only participant carrying one class, a valid class-complete participant split is impossible. Even if both classes occur in two or more participants, five participants yield only a few independent groups and unstable estimates. Do not split repetitions randomly or report them as independent test observations.

Before training, tabulate eligible alignment labels by participant and require both classes in at least two participants each, matching the loader's requirement. Use grouped leave-one-participant-out or a predeclared grouped split for exploratory estimates, report each held-out participant and per-participant metrics, and show uncertainty/class counts. With n=5 these are pilot results, not a robust generalization claim. P04's one Bad sample should be explicitly shown in counts and sensitivity analysis. Collect more participants, especially with multiple Bad alignment repetitions per participant, before making a stable participant-level performance claim.

## Provenance and next audit step

`audit_frontal_fppa.py` is read-only and already compares source/current labels, review flags, annotator/time, and error labels. Its live run failed because network access to the configured database was denied. Once the database is accessible, run it and preserve the output with dataset ID, timestamp, and code revision. Also inspect original recording instructions/annotation records to establish the intended source-folder rubric. Until that evidence exists, the source labels' substantive meaning is **unknown**.
