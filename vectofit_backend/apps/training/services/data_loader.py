import random
import re
from collections import Counter, defaultdict
from itertools import combinations

from apps.analytics.services.features import (
    FeatureExtractionError,
    extract_features_for_rep,
    model_version_for,
    to_feature_row,
    validate_features,
)
from apps.datasets.models import Dataset, DatasetSample, DatasetVideo


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
        exclusion_counts=None,
        model_version="",
        pipeline_config_hashes=None,
    ):
        self.exclusion_counts = dict(exclusion_counts or {})
        self.model_version = model_version
        self.pipeline_config_hashes = dict(pipeline_config_hashes or {})
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


def _load_labelled_samples(dataset, view_angle):
    samples = DatasetSample.objects.select_related(
        "rep_assessment__session__body_profile",
        "dataset_video__participant",
        "dataset_video__view_angle",
    ).filter(dataset=dataset, is_correct__isnull=False)

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
        yield sample, rep, rep.session


def _participant_id_for_sample(sample, dataset):
    if sample.dataset_video_id and sample.dataset_video.participant_id is not None:
        return sample.dataset_video.participant_id
    return dataset.participant_id


def _normalise_error_label(value):
    value = (value or "").strip().casefold()
    return re.sub(r"\s+", "_", value)


def build_samples(
    datasets,
    selected_features,
    view_angle=None,
    prediction_target="binary_form",
    model_version=None,
    allow_mixed_pipeline=False,
):
    if prediction_target not in {"binary_form", "error_type"}:
        raise TrainingConfigurationError(
            "prediction_target must be 'binary_form' or 'error_type'."
        )

    try:
        selected_features = validate_features(
            list(selected_features) if selected_features else None,
            model_version=model_version or "M1",
        )
    except FeatureExtractionError as exc:
        raise TrainingConfigurationError(str(exc)) from exc
    model_version = model_version or model_version_for(selected_features)

    view_angle = _resolve_view_angle(datasets, view_angle)
    _validate_training_datasets(datasets, view_angle)

    rows, labels, groups, sample_ids, sample_metadata = [], [], [], [], []
    warnings, errors = [], []
    exclusions = Counter()
    config_hashes = Counter()

    datasets_without_rows = []
    for dataset in datasets:
        dataset_row_start = len(rows)
        for sample, rep, session in _load_labelled_samples(dataset, view_angle):
            where = f"Dataset {dataset.pk}, sample {sample.pk}"

            def exclude(reason, detail=None, where=where):
                exclusions[reason] += 1
                errors.append(f"{where}: {detail or reason}")

            participant_id = _participant_id_for_sample(sample, dataset)
            if participant_id is None:
                exclude(
                    "no_participant",
                    "no participant is assigned to the video or legacy dataset.",
                )
                continue

            if prediction_target == "binary_form":
                target = 1 if sample.is_correct else 0
            elif sample.is_correct:
                target = "correct_form"
            else:
                target = _normalise_error_label(sample.error_label)
                if not target:
                    exclude(
                        "missing_error_label",
                        "incorrect form has no error_label and was excluded "
                        "from error_type training.",
                    )
                    continue
                if target == "correct_form":
                    exclude(
                        "reserved_error_label",
                        "'correct_form' is reserved for correct repetitions and "
                        "cannot be an error_label.",
                    )
                    continue

            try:
                extracted = extract_features_for_rep(
                    rep.landmark_data,
                    frame_width=session.processed_frame_width,
                    frame_height=session.processed_frame_height,
                    requested=selected_features,
                    model_version=model_version,
                )
                row = to_feature_row(extracted, selected_features)
            except FeatureExtractionError as exc:
                exclude(str(exc))
                continue

            group = f"participant-{participant_id}"
            rows.append(row)
            labels.append(target)
            groups.append(group)
            sample_ids.append(sample.pk)
            config_hashes[rep.pipeline_config_hash or ""] += 1
            video = sample.dataset_video if sample.dataset_video_id else None
            sample_metadata.append(
                {
                    "sample_id": sample.pk,
                    "rep_assessment_id": rep.pk,
                    "pipeline_config_hash": rep.pipeline_config_hash or "",
                    "dataset_id": dataset.pk,
                    "dataset_name": dataset.name,
                    "dataset_video_id": sample.dataset_video_id,
                    "source_path": video.source_path if video else "",
                    "source_label": video.source_label if video else None,
                    "participant_id": participant_id,
                    "participant_group": group,
                    "view_angle": view_angle,
                    "is_correct": sample.is_correct,
                    "label_source": sample.label_source,
                    "error_label": sample.error_label or "",
                    "annotator_id": sample.annotator_id,
                    "annotated_at": sample.annotated_at.isoformat()
                    if sample.annotated_at
                    else None,
                    "target": target,
                    "label_origin": (
                        "human"
                        if sample.annotator_id is not None
                        or sample.annotated_at is not None
                        or sample.label_source in {"consensus", "adjudicated"}
                        else "source_or_inherited"
                    ),
                }
            )

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

    if len(config_hashes) > 1 and not allow_mixed_pipeline:
        summary = ", ".join(
            f"{(digest[:12] or '(none)')}: {count} rep(s)"
            for digest, count in sorted(config_hashes.items())
        )
        raise TrainingConfigurationError(
            "The selected repetitions were produced by different preprocessing "
            f"pipelines (pipeline_config_hash -> {summary}). Re-process them with "
            "the frozen pipeline, or pass allow_mixed_pipeline=True to override."
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
        if errors:
            detail += " " + " ".join(errors[:10])
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
        exclusion_counts=exclusions,
        model_version=model_version,
        pipeline_config_hashes=config_hashes,
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
                "Cannot create a participant-level split: participant coverage for target classes is "
                f"insufficient across participants ({coverage}). Dataset has "
                f"{len(group_ids)} participants and {total_samples} usable samples; "
                f"class sample counts are {sample_counts}. Collect samples for the "
                "underrepresented class from at least two participants."
            )

    best = None

    if len(group_ids) <= 20:
        for size in range(1, len(group_ids)):
            for selected in combinations(group_ids, size):
                test_group_set = set(selected)
                test_indices = sorted(i for g in test_group_set for i in by_group[g])
                train_indices = sorted(
                    i for g in group_ids if g not in test_group_set for i in by_group[g]
                )
                if labels is not None:
                    if {labels[i] for i in test_indices} != target_classes or {
                        labels[i] for i in train_indices
                    } != target_classes:
                        continue
                test_distribution = defaultdict(int)
                if labels is not None:
                    for i in test_indices:
                        test_distribution[labels[i]] += 1
                    class_penalty = sum(
                        abs(
                            test_distribution[label] / len(test_indices)
                            - sum(1 for y in labels if y == label) / len(labels)
                        )
                        for label in target_classes
                    )
                else:
                    class_penalty = 0.0
                score = (
                    abs(len(test_indices) / total_samples - test_size) + class_penalty
                )
                if best is None or score < best[0]:
                    best = (score, train_indices, test_indices)
    else:
        rng = random.Random(seed)
        for _ in range(max(1, attempts)):
            shuffled = group_ids[:]
            rng.shuffle(shuffled)
            for cutoff in range(1, len(shuffled)):
                selected = set(shuffled[:cutoff])
                test_indices = sorted(i for g in selected for i in by_group[g])
                train_indices = sorted(
                    i for g in group_ids if g not in selected for i in by_group[g]
                )
                if labels is not None and (
                    {labels[i] for i in test_indices} != target_classes
                    or {labels[i] for i in train_indices} != target_classes
                ):
                    continue
                score = abs(len(test_indices) / total_samples - test_size)
                if best is None or score < best[0]:
                    best = (score, train_indices, test_indices)

    if best is None:
        class_detail = (
            f" Target classes have participant coverage {class_group_counts}; "
            "every class must appear in both partitions."
            if labels is not None
            else ""
        )
        raise InsufficientGroupsError(
            "Could not create a non-empty participant-level train/test split after "
            f"searching {('all participant subsets' if len(group_ids) <= 20 else f'{max(1, attempts)} bounded randomized attempts')}. "
            f"Dataset has {len(group_ids)} participants and {total_samples} samples."
            + class_detail
            + (
                " Increase attempts or reduce the participant count if this is a computationally bounded search."
                if len(group_ids) > 20
                else ""
            )
        )

    return best[1], best[2]


def leave_one_participant_out_folds(groups, labels):
    if len(groups) != len(labels):
        raise InsufficientGroupsError(
            "Cannot build folds: groups and labels must contain the same number "
            f"of entries (got {len(groups)} groups and {len(labels)} labels)."
        )
    by_group = defaultdict(list)
    for index, group in enumerate(groups):
        by_group[group].append(index)
    group_ids = sorted(by_group)
    if len(group_ids) < 2:
        raise InsufficientGroupsError(
            "Leave-one-participant-out needs at least two participants; found "
            f"{len(group_ids)}."
        )

    classes = set(labels)
    folds, skipped = [], []
    for group_id in group_ids:
        test_idx = by_group[group_id]
        held_out = set(test_idx)
        train_idx = [i for i in range(len(groups)) if i not in held_out]
        if {labels[i] for i in train_idx} != classes:
            skipped.append(
                {"group": group_id, "reason": "training_split_missing_class"}
            )
            continue
        folds.append(
            {"group": group_id, "train_idx": train_idx, "test_idx": list(test_idx)}
        )
    if len(folds) < 2:
        raise InsufficientGroupsError(
            "Fewer than two participants could be evaluated: removing a "
            "participant left the training set without every target class "
            f"({len(skipped)} of {len(group_ids)} participants skipped)."
        )
    return folds, skipped


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
