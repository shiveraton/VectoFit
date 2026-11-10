from django.db import transaction
from django.db.models import F, Q
from rest_framework.exceptions import ValidationError

from ..models import Dataset, DatasetAnnotatorAssignment, DatasetAssignmentEvent, DatasetSample
from .frontal import frontal_samples


@transaction.atomic
def set_assignment(dataset, annotator, is_active, actor):
    Dataset.objects.select_for_update().get(pk=dataset.pk)
    if is_active and (
        not annotator.is_active
        or annotator.is_staff
        or annotator.is_superuser
        or not getattr(getattr(annotator, "profile", None), "is_annotator", False)
    ):
        raise ValidationError({"annotator": "Choose an active, non-staff annotator."})
    assignment = DatasetAnnotatorAssignment.objects.filter(
        dataset=dataset, annotator=annotator
    ).first()
    if assignment is None and not is_active:
        return None
    if assignment is not None and assignment.is_active == is_active:
        return assignment
    if assignment is None:
        assignment = DatasetAnnotatorAssignment.objects.create(
            dataset=dataset, annotator=annotator
        )
    else:
        assignment.is_active = is_active
        assignment.save(update_fields=["is_active"])
    DatasetAssignmentEvent.objects.create(
        assignment=assignment,
        actor=actor,
        action=DatasetAssignmentEvent.Action.GRANTED
        if is_active
        else DatasetAssignmentEvent.Action.REVOKED,
    )
    return assignment


def review_samples():
    return frontal_samples(DatasetSample.objects.filter(dataset__status="READY")).filter(
        Q(dataset_video__isnull=True)
        | Q(dataset_video__status="READY", dataset_video__requires_manual_review=True,
            dataset_video__dataset_id=F("dataset_id"))
    )


def assigned_samples(user):
    assignments = DatasetAnnotatorAssignment.objects.filter(
        annotator=user, is_active=True,
    ).values("dataset_id")
    return DatasetSample.objects.filter(dataset_id__in=assignments)


def assigned_review_samples(user):
    return review_samples().filter(pk__in=assigned_samples(user).values("pk"))
