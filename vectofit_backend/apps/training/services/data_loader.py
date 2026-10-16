import random
from collections import defaultdict

from apps.analytics.services.features import (
    FeatureExtractionError,
    extract_rep_features,
    to_feature_row,
)
from apps.datasets.models import Dataset, DatasetSample

class DatasetNotUsableError(Exception):
    pass

class SampleSet:
    def __init__(self, features, rows, labels, groups, feature_names, warnings, errors):
        self.features = features
        self.rows = rows
        self.labels = labels
        self.groups = groups
        self.feature_names = feature_names
        self.warnings = warnings
        self.errors = errors

    def __len__(self):
        return len(self.rows)

    @property
    def class_distribution(self):
        counts = defaultdict(int)
        for label in self.labels:
            counts[int(label)] += 1
        return dict(counts)


def _frames_from_landmark_series(raw):
    frames = []
    for entry in raw or []:
        frame = entry.get("landmarks") if isinstance(entry, dict) and "landmarks" in entry else entry
        if frame:
            frames.append(frame)
    return frames


def _scale_factor_for_session(session):
    if session is None or session.body_profile_id is None:
        return None
    return session.body_profile.scale_factor or None


def _load_labelled_samples(dataset):
    samples = (
        DatasetSample.objects.select_related(
            "rep_assessment__session",
            "rep_assessment__session__body_profile",
            "dataset_video__participant"
        )
        .filter(dataset=dataset, is_correct__isnull=False)
        .order_by("id")
    )

    for sample in samples:
        rep = sample.rep_assessment
        frames = _frames_from_landmark_series(rep.landmark_series)
        if len(frames) < 3:
            continue
        yield sample, frames, rep.session


def build_samples(datasets, selected_features):
    rows = []
    labels = []
    groups = []
    warnings = []
    errors = []

    for dataset in datasets:
        found_any = False

        for sample, frames, session in _load_labelled_samples(dataset):
            if sample.dataset_video_id:
                participant_id = (
                    sample.dataset_video.participant_id
                )
            else:
                participant_id = dataset.participant_id

            if participant_id is None:
                errors.append(
                    f"Dataset {dataset.pk} sample ({sample.pk}) has no participant assigned."
                )
                continue

            found_any = True

            try:
                features = extract_rep_features(
                    frames,
                    fps=30.0,
                    scale_factor=_scale_factor_for_session(session),
                )
                row = to_feature_row(features, selected_features)

            except FeatureExtractionError as exc:
                errors.append(f"Dataset {dataset.pk} sample {sample.pk}: {exc}")
                continue

            rows.append(row)
            labels.append(1 if sample.is_correct else 0)
            groups.append(f"participant-{participant_id}")

            for warning in features.get("_warnings", []):
                if warning not in warnings:
                    warnings.append(warning)

        if not found_any:
            errors.append(
                f"Dataset {dataset.pk} ({dataset.name!r}) has no labelled "
                f"repetitions: DatasetSample.is_correct must be set before training."
            )

    if not rows:
        raise DatasetNotUsableError(
            "No usable ML samples could be built from the selected datasets. "
            + " | ".join(errors[:10])
        )

    return SampleSet(
        features=selected_features,
        rows=rows,
        labels=labels,
        groups=groups,
        feature_names=list(selected_features),
        warnings=warnings,
        errors=errors,
    )


def group_split(groups, test_size=0.3, seed=42):
    by_group = defaultdict(list)
    for index, group in enumerate(groups):
        by_group[group].append(index)

    group_ids = sorted(by_group)
    rng = random.Random(seed)
    rng.shuffle(group_ids)

    total = len(groups)
    target_test = max(1, int(round(total * test_size)))

    test_groups = []
    test_total = 0
    for group_id in group_ids:
        if test_total >= target_test:
            break
        test_groups.append(group_id)
        test_total += len(by_group[group_id])

    test_set = set(test_groups)
    test_idx = sorted(i for g in test_groups for i in by_group[g])
    train_idx = sorted(
        i for g in group_ids if g not in test_set for i in by_group[g]
    )

    return train_idx, test_idx


class TrainingConfigurationError(Exception):
    pass

def resolve_datasets(dataset_ids: list[int]) -> list[Dataset]:
    if not dataset_ids:
        raise TrainingConfigurationError("At least one dataset ID must be provided.")

    unique_ids = list(dict.fromkeys(dataset_ids))
    datasets = list(Dataset.objects.filter(pk__in=unique_ids))

    found_ids = {d.pk for d in datasets}
    missing_ids = set(unique_ids) - found_ids
    if missing_ids:
        raise TrainingConfigurationError(f"Dataset IDs not found in the database: {sorted(missing_ids)}")

    return datasets