import random
import re
import math
import statistics
from collections import Counter, defaultdict
from itertools import combinations

import cv2
from apps.analytics.services import fppa
from apps.analytics.services.feature_schemas import schema_for_target
from apps.analytics.services.features import (
    FeatureExtractionError,
    extract_rep_features,
    to_feature_row,
)
from apps.datasets.models import Dataset, DatasetSample, DatasetVideo
from apps.datasets.services.knee_label import (
    knee_label_evidence,
)


class DatasetNotUsableError(Exception):
    """Raised when a dataset cannot produce usable ML samples."""


class InsufficientGroupsError(DatasetNotUsableError):
    """Raised when participant-based splitting is not possible."""


class TrainingConfigurationError(Exception):
    """Raised when the training configuration is invalid."""


class SampleSet:
    def __init__(
        self,
        features,
        rows,
        labels,
        groups,
        feature_names,
        warnings,
        errors,
        sample_ids=None,
        sample_metadata=None,
        prediction_target="binary_form",
        view_angle="",
    ):
        self.features = features
        self.rows = rows
        self.labels = labels
        self.groups = groups
        self.feature_names = feature_names
        self.warnings = warnings
        self.errors = errors
        self.sample_ids = list(sample_ids or [])
        self.sample_metadata = list(sample_metadata or [])
        self.prediction_target = prediction_target
        self.view_angle = view_angle

    def __len__(self):
        return len(self.rows)

    @property
    def class_distribution(self):
        counts = defaultdict(int)
        for label in self.labels:
            counts[str(label)] += 1
        return dict(counts)


def _frames_from_landmark_series(raw):
    frames = []
    for entry in raw or []:
        frame = (
            entry.get("landmarks")
            if isinstance(entry, dict) and "landmarks" in entry
            else entry
        )
        if frame:
            frames.append(frame)
    return frames


def _fppa_frames_from_landmark_series(raw):
    frames = []
    for entry in raw or []:
        if not isinstance(entry, dict):
            continue
        if isinstance(entry.get("landmarks"), dict):
            frames.append(entry)
        else:
            frames.append({"landmarks": entry})
    return frames


def _scale_factor_for_session(session):
    if session is None or session.body_profile_id is None:
        return None
    return session.body_profile.scale_factor or None


def _training_frame_rate(sample, dataset):
    raw = sample.rep_assessment.landmark_series or []
    entries = [entry for entry in raw if isinstance(entry, dict)]

    timestamps = [entry.get("timestamp_ms") for entry in entries]
    if any(value is not None for value in timestamps):
        try:
            values = [float(value) for value in timestamps]
        except (TypeError, ValueError) as exc:
            raise FeatureExtractionError("Frame timestamps are invalid.") from exc
        if len(values) < 2 or not all(math.isfinite(value) for value in values):
            raise FeatureExtractionError(
                "At least two finite frame timestamps are required."
            )
        intervals = [right - left for left, right in zip(values, values[1:])]
        if any(interval <= 0 for interval in intervals):
            raise FeatureExtractionError(
                "Frame timestamps must be strictly increasing."
            )
        return 1000.0 / statistics.median(intervals), "frame_timestamps"

    frame_indices = [entry.get("frame_index") for entry in entries]
    source_rates = [entry.get("native_fps") for entry in entries]
    if all(value is not None for value in frame_indices) and any(
        value is not None for value in source_rates
    ):
        try:
            indices = [int(value) for value in frame_indices]
            source_fps = float(
                next(value for value in source_rates if value is not None)
            )
        except (TypeError, ValueError, StopIteration) as exc:
            raise FeatureExtractionError("Frame timing metadata is invalid.") from exc
        intervals = [right - left for left, right in zip(indices, indices[1:])]
        if (
            len(intervals) == 0
            or any(interval <= 0 for interval in intervals)
            or not math.isfinite(source_fps)
            or source_fps <= 0
        ):
            raise FeatureExtractionError("Frame timing metadata is invalid.")
        return source_fps / statistics.median(intervals), "frame_indices_and_source_fps"

    video_candidates = []
    if sample.dataset_video_id and sample.dataset_video.video_file:
        video_candidates.append(sample.dataset_video.video_file)
    if sample.rep_assessment.session.video_file:
        video_candidates.append(sample.rep_assessment.session.video_file)
    if dataset.video_file:
        video_candidates.append(dataset.video_file)

    for video_file in video_candidates:
        capture = None
        try:
            capture = cv2.VideoCapture(video_file.path)
            source_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        except (OSError, ValueError, NotImplementedError, cv2.error):
            continue
        finally:
            if capture is not None:
                capture.release()
        if math.isfinite(source_fps) and source_fps > 0:
            sample_step = max(1, round(source_fps / 30.0))
            return source_fps / sample_step, "source_video_fps_sampled_at_30fps"

    raise FeatureExtractionError(
        "No usable frame timestamps or source video FPS are available for velocity features."
    )


def _available_angles(dataset):
    angles = set(
        dataset.videos.filter(status=DatasetVideo.Status.READY)
        .values_list("view_angle__angle_variant", flat=True)
        .distinct()
    )
    if not dataset.videos.exists() and dataset.view_angle_id and dataset.view_angle:
        angles.add(dataset.view_angle.angle_variant)
    return {angle for angle in angles if angle}


def _resolve_view_angle(datasets, view_angle):
    if view_angle:
        if view_angle not in {"diagonal", "frontal", "sagittal"}:
            raise TrainingConfigurationError(
                "view_angle must be one of: diagonal, frontal, sagittal."
            )
        return view_angle

    available = set()
    for dataset in datasets:
        available.update(_available_angles(dataset))
    if len(available) != 1:
        raise TrainingConfigurationError(
            "Select a camera angle explicitly. The selected datasets expose "
            f"these angles: {sorted(available) or ['none']}."
        )
    return next(iter(available))


def _validate_training_datasets(datasets, view_angle):
    invalid = []
    for dataset in datasets:
        if dataset.purpose != "training":
            invalid.append(
                f"{dataset.name}: purpose is {dataset.purpose!r}, not 'training'"
            )
        if dataset.status != "READY":
            invalid.append(f"{dataset.name}: status is {dataset.status!r}, not 'READY'")
        if view_angle not in _available_angles(dataset):
            invalid.append(
                f"{dataset.name}: no READY videos/samples for {view_angle!r} view"
            )
    if invalid:
        raise TrainingConfigurationError(
            "Selected datasets are not compatible with this training run: "
            + "; ".join(invalid)
        )


def _load_labelled_samples(dataset, view_angle, prediction_target):
    samples = DatasetSample.objects.select_related(
        "rep_assessment__session__body_profile",
        "dataset_video__participant",
        "dataset_video__view_angle",
    ).filter(dataset=dataset)
    if prediction_target != "knee_alignment":
        samples = samples.filter(is_correct__isnull=False)

    if dataset.videos.exists():
        samples = samples.filter(
            dataset_video__view_angle__angle_variant=view_angle,
            dataset_video__status=DatasetVideo.Status.READY,
        )
    else:
        samples = samples.filter(
            dataset_video__isnull=True,
            dataset__view_angle__angle_variant=view_angle,
        )

    samples = samples.order_by("id")
    for sample in samples:
        rep = sample.rep_assessment
        frames = _frames_from_landmark_series(rep.landmark_series)
        if len(frames) < 3:
            continue
        yield sample, frames, rep.session


def _participant_id_for_sample(sample, dataset):
    if sample.dataset_video_id and sample.dataset_video.participant_id is not None:
        return sample.dataset_video.participant_id
    return dataset.participant_id


def _normalise_error_label(value):
    value = (value or "").strip().casefold()
    return re.sub(r"\s+", "_", value)


def _extract_sample_features(
    sample,
    frames,
    session,
    dataset,
    schema_version,
    fallback_frame_width,
    fallback_frame_height,
):
    if schema_version == fppa.FEATURE_SCHEMA_VERSION:
        fppa_frames = _fppa_frames_from_landmark_series(
            sample.rep_assessment.landmark_series
        )
        frame_width = next(
            (
                int(frame["source_width"])
                for frame in fppa_frames
                if frame.get("source_width")
            ),
            fallback_frame_width,
        )
        frame_height = next(
            (
                int(frame["source_height"])
                for frame in fppa_frames
                if frame.get("source_height")
            ),
            fallback_frame_height,
        )
        effective_fps, timing_source = _training_frame_rate(sample, dataset)
        extracted, fppa_metadata = fppa.extract_fppa_features(
            fppa_frames,
            frame_width=frame_width,
            frame_height=frame_height,
            native_fps=effective_fps,
        )
        if not fppa_metadata.get("valid") or extracted is None:
            raise FeatureExtractionError(
                f"FPPA extraction was invalid: {fppa_metadata.get('reason')}"
            )
    else:
        effective_fps, timing_source = _training_frame_rate(sample, dataset)
        extracted = extract_rep_features(
            frames,
            fps=effective_fps,
            scale_factor=_scale_factor_for_session(session),
        )
        fppa_metadata = None
    return extracted, fppa_metadata, timing_source


def build_samples(
    datasets,
    selected_features,
    view_angle=None,
    prediction_target="binary_form",
    *,
    fallback_frame_width=1280,
    fallback_frame_height=720,
):
    if prediction_target not in {"binary_form", "error_type", "knee_alignment"}:
        raise TrainingConfigurationError(
            "prediction_target must be 'binary_form', 'error_type', or "
            "'knee_alignment'."
        )

    view_angle = _resolve_view_angle(datasets, view_angle)
    if prediction_target == "knee_alignment" and view_angle != "frontal":
        raise TrainingConfigurationError(
            "FPPA knee-alignment training requires the frontal view."
        )
    _validate_training_datasets(datasets, view_angle)
    schema = schema_for_target(prediction_target)
    if not selected_features:
        selected_features = list(schema.feature_order)
    unknown_features = sorted(set(selected_features) - set(schema.feature_order))
    if unknown_features:
        raise TrainingConfigurationError(
            f"Features {unknown_features} are not available in {schema.version}."
        )

    rows, labels, groups, sample_ids, sample_metadata = [], [], [], [], []
    warnings, warning_set, errors = [], set(), []

    datasets_without_rows = []
    for dataset in datasets:
        dataset_row_start = len(rows)
        for sample, frames, session in _load_labelled_samples(
            dataset, view_angle, prediction_target
        ):
            participant_id = _participant_id_for_sample(sample, dataset)
            if participant_id is None:
                errors.append(
                    f"Dataset {dataset.pk}, sample {sample.pk}: no participant is "
                    "assigned to the video or legacy dataset."
                )
                continue

            evidence = (
                knee_label_evidence(sample)
                if prediction_target == "knee_alignment"
                else None
            )
            annotations = evidence["annotations"] if evidence else []
            annotator_ids = [
                record["annotator_id"]
                for record in annotations
                if record["annotator_id"] is not None
            ]
            if evidence is None:
                human_label = (
                    sample.annotator_id is not None or sample.annotated_at is not None
                )
            else:
                human_label = bool(annotations) and all(
                    record["annotator_id"] is not None for record in annotations
                )
            if prediction_target == "binary_form":
                target = 1 if sample.is_correct else 0
            elif prediction_target == "knee_alignment":
                target = evidence["target"]
                if target not in {"good", "bad"}:
                    errors.append(
                        f"Dataset {dataset.pk}, sample {sample.pk}: knee target "
                        f"{target or 'missing'} was excluded from training."
                    )
                    continue
            elif sample.is_correct:
                target = "correct_form"
            else:
                target = _normalise_error_label(sample.error_label)
                if not target:
                    errors.append(
                        f"Dataset {dataset.pk}, sample {sample.pk}: incorrect form has "
                        "no error_label and was excluded from error_type training."
                    )
                    continue
                if target == "correct_form":
                    errors.append(
                        f"Dataset {dataset.pk}, sample {sample.pk}: 'correct_form' is "
                        "reserved for correct repetitions and cannot be an error_label."
                    )
                    continue

            try:
                extracted, fppa_metadata, timing_source = _extract_sample_features(
                    sample,
                    frames,
                    session,
                    dataset,
                    schema.version,
                    fallback_frame_width,
                    fallback_frame_height,
                )
                row = to_feature_row(extracted, selected_features)
            except (FeatureExtractionError, ValueError, TypeError) as exc:
                errors.append(f"Dataset {dataset.pk}, sample {sample.pk}: {exc}")
                continue

            group = f"participant-{participant_id}"
            rows.append(row)
            labels.append(target)
            groups.append(group)
            sample_ids.append(sample.pk)
            video = sample.dataset_video if sample.dataset_video_id else None
            sample_metadata.append(
                {
                    "sample_id": sample.pk,
                    "dataset_id": dataset.pk,
                    "dataset_name": dataset.name,
                    "dataset_video_id": sample.dataset_video_id,
                    "source_path": video.source_path if video else "",
                    "source_label": video.source_label if video else None,
                    "participant_id": participant_id,
                    "participant_group": group,
                    "view_angle": view_angle,
                    "timing_source": timing_source,
                    "is_correct": sample.is_correct,
                    "error_label": sample.error_label or "",
                    "annotator_id": sample.annotator_id,
                    "annotator_ids": annotator_ids,
                    "knee_annotations": annotations,
                    "annotated_at": sample.annotated_at.isoformat()
                    if sample.annotated_at
                    else None,
                    "target": target,
                    "label_origin": "human" if human_label else "source_or_inherited",
                }
            )
            if fppa_metadata is not None:
                sample_metadata[-1]["fppa_metadata"] = fppa_metadata

            for warning in extracted.get("_warnings", []):
                if warning not in warning_set:
                    warnings.append(warning)
                    warning_set.add(warning)

        if len(rows) == dataset_row_start:
            message = (
                f"Dataset {dataset.pk} ({dataset.name!r}) contributed no usable "
                f"repetitions for the {view_angle!r} angle and target "
                f"{prediction_target!r}. Check labels, video status, error labels, "
                "participant assignments, and landmark completeness."
            )
            errors.append(message)
            datasets_without_rows.append(message)

    if datasets_without_rows:
        raise DatasetNotUsableError(" ".join(datasets_without_rows[:10]))

    if not rows:
        details = " | ".join(errors[:10])
        raise DatasetNotUsableError(
            "No usable training samples were built from the selected datasets. "
            + details
        )

    class_set = set(labels)
    if len(class_set) < 2:
        detail = "The selected data contains only one target class."
        if prediction_target == "error_type":
            detail += (
                " Add correct_form samples and at least one labelled error category."
            )
        else:
            detail += " Include both correct and incorrect repetitions."
        raise DatasetNotUsableError(detail)

    return SampleSet(
        features=selected_features,
        rows=rows,
        labels=labels,
        groups=groups,
        feature_names=list(selected_features),
        warnings=warnings,
        errors=errors,
        sample_ids=sample_ids,
        sample_metadata=sample_metadata,
        prediction_target=prediction_target,
        view_angle=view_angle,
    )


def group_split(groups, test_size=0.3, seed=42, labels=None, attempts=512):
    if not 0 < test_size < 1:
        raise TrainingConfigurationError(
            "test_size must be greater than 0 and less than 1."
        )
    if not groups:
        raise InsufficientGroupsError("Cannot split an empty sample set.")
    if labels is not None and len(labels) != len(groups):
        raise InsufficientGroupsError(
            "Cannot split samples: groups and labels must contain the same number "
            f"of entries (got {len(groups)} groups and {len(labels)} labels)."
        )

    total_samples = len(groups)
    by_group = defaultdict(list)
    for index, group in enumerate(groups):
        by_group[group].append(index)
    group_ids = sorted(by_group)
    if len(group_ids) < 2:
        raise InsufficientGroupsError(
            "Cannot create a participant-level split: found only "
            f"{len(group_ids)} participant and {total_samples} usable samples. "
            "At least two participants are required; repetitions from one participant "
            "do not provide independent participant coverage."
        )

    target_classes = set(labels) if labels is not None else set()
    group_class_counts = {}
    class_group_counts = {}
    if labels is not None:
        class_groups = defaultdict(set)
        for group_id in group_ids:
            counts = defaultdict(int)
            for index in by_group[group_id]:
                counts[labels[index]] += 1
                class_groups[labels[index]].add(group_id)
            group_class_counts[group_id] = dict(counts)
        class_group_counts = {
            label: len(class_groups[label]) for label in sorted(target_classes, key=str)
        }
        lacking = [label for label in target_classes if len(class_groups[label]) < 2]
        if lacking:
            coverage = "; ".join(
                f"{label!r}: {class_group_counts[label]} participant(s)"
                for label in sorted(lacking, key=str)
            )
            sample_counts = {
                label: sum(1 for value in labels if value == label)
                for label in sorted(target_classes, key=str)
            }
            raise InsufficientGroupsError(
                "Cannot create a participant-level split: target class participant coverage "
                f"is insufficient ({coverage}). Dataset has "
                f"{len(group_ids)} participants and {total_samples} usable samples; "
                f"class sample counts are {sample_counts}. Collect samples for the "
                "underrepresented class from at least two participants."
            )

    exact_search = len(group_ids) <= 12
    if exact_search:
        candidates = (
            selected
            for size in range(1, len(group_ids))
            for selected in combinations(group_ids, size)
        )
    else:

        def random_candidates():
            rng = random.Random(seed)
            for _ in range(max(1, attempts)):
                shuffled = group_ids[:]
                rng.shuffle(shuffled)
                for cutoff in range(1, len(shuffled)):
                    yield shuffled[:cutoff]

        candidates = random_candidates()

    overall_counts = Counter(labels) if labels is not None else Counter()
    best = None
    for selected in candidates:
        test_counts = Counter()
        test_count = 0
        for group in selected:
            test_count += len(by_group[group])
            test_counts.update(group_class_counts.get(group, {}))
        if labels is not None and any(
            test_counts[label] == 0 or test_counts[label] == overall_counts[label]
            for label in target_classes
        ):
            continue
        class_penalty = sum(
            abs(test_counts[label] / test_count - overall_counts[label] / total_samples)
            for label in target_classes
        )
        score = abs(test_count / total_samples - test_size) + class_penalty
        if best is None or score < best[0]:
            best = (score, set(selected))

    if best is None:
        search = (
            "all participant subsets"
            if exact_search
            else f"{max(1, attempts)} bounded randomized attempts"
        )
        raise InsufficientGroupsError(
            f"Could not create a non-empty participant-level train/test split after searching {search}. "
            f"Dataset has {len(group_ids)} participants and {total_samples} samples. "
            f"Target classes have participant coverage {class_group_counts}; "
            "every class must appear in both partitions."
        )

    test_groups = best[1]
    train_indices = [i for i, group in enumerate(groups) if group not in test_groups]
    test_indices = [i for i, group in enumerate(groups) if group in test_groups]
    return train_indices, test_indices


def resolve_datasets(dataset_ids: list[int]) -> list[Dataset]:
    if not dataset_ids:
        raise TrainingConfigurationError("At least one dataset ID must be provided.")
    unique_ids = list(dict.fromkeys(dataset_ids))
    datasets = list(
        Dataset.objects.select_related("view_angle")
        .filter(pk__in=unique_ids)
        .prefetch_related("videos__view_angle")
    )
    found_ids = {dataset.pk for dataset in datasets}
    missing_ids = set(unique_ids) - found_ids
    if missing_ids:
        raise TrainingConfigurationError(
            f"Dataset IDs not found in the database: {sorted(missing_ids)}"
        )
    by_id = {dataset.pk: dataset for dataset in datasets}
    return [by_id[pk] for pk in unique_ids]
