from collections import Counter
from collections.abc import Mapping

from apps.datasets.models import AnnotationEvent, KneeAnnotation
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .annotation import derive_target_label

CONSENSUS_LABELS = {"good", "bad", "borderline", "unassessable"}
TRAINABLE_LABELS = {"good", "bad"}
CONSENSUS_STATUSES = {"resolved", "insufficient", "disagreement", "not_trainable"}


def validate_consensus_result(result):
    """Reject malformed evaluator output before it can mutate a sample."""
    if not isinstance(result, Mapping):
        raise ValueError("Consensus result must be a mapping.")
    status = result.get("status")
    label = result.get("label")
    labels = result.get("labels")
    if status not in CONSENSUS_STATUSES:
        raise ValueError(f"Unsupported consensus status: {status!r}.")
    if not isinstance(labels, Mapping):
        raise ValueError("Consensus result labels must be a mapping.")
    if any(value not in CONSENSUS_LABELS for value in labels.values()):
        raise ValueError("Consensus result contains an unsupported annotator label.")
    if status == "resolved":
        if label not in TRAINABLE_LABELS:
            raise ValueError("A resolved consensus label must be 'good' or 'bad'.")
    elif status == "not_trainable":
        if label not in CONSENSUS_LABELS - TRAINABLE_LABELS:
            raise ValueError(
                "A not_trainable result must be 'borderline' or 'unassessable'."
            )
    elif label is not None:
        raise ValueError(f"A {status!r} result must have a null label.")
    return status, label, labels


def _validated_source_label(video):
    value = video.source_label
    if value is not None and type(value) is not bool:
        raise ValueError("DatasetVideo.source_label must be a bool or None.")
    return value


def base_label_for_sample(sample):
    video = sample.dataset_video
    if video is None:
        return None
    source_label = _validated_source_label(video)
    if video.requires_manual_review:
        return None
    return source_label


def evaluate_sample(sample, min_annotators=None):
    min_annotators = min_annotators or getattr(settings, "ANNOTATION_MIN_ANNOTATORS", 2)
    labels = {
        str(row.annotator_id): label
        for row in KneeAnnotation.objects.filter(sample=sample).select_related(
            "annotator"
        )
        if row.annotator_id is not None
        for label in [derive_target_label(row.annotation)]
        if label is not None
    }
    if len(labels) < min_annotators:
        return {"status": "insufficient", "label": None, "labels": labels}
    counts = Counter(labels.values())
    winner, count = counts.most_common(1)[0]
    if count * 2 <= len(labels):
        return {"status": "disagreement", "label": None, "labels": labels}
    if winner not in {"good", "bad"}:
        return {"status": "not_trainable", "label": winner, "labels": labels}
    return {"status": "resolved", "label": winner, "labels": labels}


@transaction.atomic
def apply_consensus(sample, result, entered_by=None, force=False):
    """Apply evaluator output.

    ``force`` only overrides an ``adjudicated`` protection: a resolved result
    replaces it with consensus, while a non-resolved result clears that label
    and restores the video source label (or NULL for manual-review/no-video
    samples). For every other source, force has no extra effect.
    """
    status, label, annotator_labels = validate_consensus_result(result)
    video = sample.dataset_video
    if video is not None:
        _validated_source_label(video)
    if not isinstance(force, bool):
        raise ValueError("force must be a bool.")
    if sample.label_source == "adjudicated" and not force:
        return False
    mapping = getattr(
        settings, "ANNOTATION_TARGET_TO_IS_CORRECT", {"good": True, "bad": False}
    )
    previous_consensus = sample.label_source == "consensus" or (
        force and sample.label_source == "adjudicated"
    )
    if status == "resolved":
        if not isinstance(mapping, Mapping) or any(
            key not in mapping or type(mapping[key]) is not bool
            for key in TRAINABLE_LABELS
        ):
            raise ValueError(
                "ANNOTATION_TARGET_TO_IS_CORRECT must map good and bad to bool values."
            )
        sample.is_correct = mapping[label]
        sample.label_source = "consensus"
        sample.annotated_at = timezone.now()
        sample.annotator = None
        sample.save(
            update_fields=["is_correct", "label_source", "annotated_at", "annotator"]
        )
        AnnotationEvent.objects.create(
            sample=sample,
            annotator=None,
            entered_by=entered_by,
            action=AnnotationEvent.Action.RESOLVE,
            target_label=label,
            payload={"annotator_labels": annotator_labels, "result": label},
            rubric_version=getattr(settings, "ANNOTATION_RUBRIC_VERSION", "v1"),
        )
        return True
    if previous_consensus:
        sample.is_correct = base_label_for_sample(sample)
        sample.label_source = ""
        sample.annotator = None
        sample.annotated_at = None
        sample.save(
            update_fields=["is_correct", "label_source", "annotator", "annotated_at"]
        )
        AnnotationEvent.objects.create(
            sample=sample,
            annotator=None,
            entered_by=entered_by,
            action=AnnotationEvent.Action.RESOLVE,
            target_label="",
            payload={
                "annotator_labels": annotator_labels,
                "result": status,
                "reset": True,
            },
            rubric_version=getattr(settings, "ANNOTATION_RUBRIC_VERSION", "v1"),
        )
        return True
    return False
