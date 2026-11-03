from apps.datasets.models import AnnotationEvent, KneeAnnotation
from django.conf import settings
from django.db import transaction


def derive_target_label(annotation):
    if not annotation:
        return None

    valid_grades = {"aligned", "borderline", "deviated", "unassessable"}

    grades = [annotation.get(side, {}).get("grade") for side in ("left", "right")]

    if any(grade is None for grade in grades):
        return None

    if any(grade not in valid_grades for grade in grades):
        return None

    if "unassessable" in grades:
        return "unassessable"

    if "borderline" in grades:
        return "borderline"

    return "bad" if "deviated" in grades else "good"


def _event(sample, user, action, annotation):
    return AnnotationEvent.objects.create(
        sample=sample,
        annotator=user,
        entered_by=user,
        action=action,
        target_label=derive_target_label(annotation) or "",
        payload=annotation,
        rubric_version=getattr(settings, "ANNOTATION_RUBRIC_VERSION", "v1"),
    )


@transaction.atomic
def save_annotation(sample, user, annotation):
    if user is None or not getattr(user, "is_authenticated", False):
        raise ValueError("An authenticated annotator is required.")
    record = KneeAnnotation.objects.filter(sample=sample, annotator=user).first()
    if record and record.annotation == annotation:
        return record
    if record:
        record.annotation = annotation
        record.save(update_fields=["annotation", "updated_at"])
    else:
        record = KneeAnnotation.objects.create(
            sample=sample, annotator=user, annotation=annotation
        )
    _event(sample, user, AnnotationEvent.Action.SAVE, annotation)
    return record


@transaction.atomic
def clear_annotation(sample, user):
    if user is None or not getattr(user, "is_authenticated", False):
        raise ValueError("An authenticated annotator is required.")
    record = KneeAnnotation.objects.filter(sample=sample, annotator=user).first()
    if record:
        snapshot = record.annotation
        record.delete()
        _event(sample, user, AnnotationEvent.Action.CLEAR, snapshot)
