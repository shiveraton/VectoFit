from django.contrib.auth import get_user_model

from ..models import DatasetSample

User = get_user_model()


def latest_annotation(sample: DatasetSample, user: User | None):
    records = sample.knee_annotation_records.order_by("-created_at", "-id")
    if user is not None:
        records = records.filter(annotator=user)
    return records.first()
