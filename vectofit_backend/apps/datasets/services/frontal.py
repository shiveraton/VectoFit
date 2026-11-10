from django.db.models import Q
from rest_framework.exceptions import ValidationError


def frontal_samples(samples):
    return samples.filter(
        Q(dataset_video__view_angle__angle_variant="frontal")
        | Q(dataset_video__isnull=True, dataset__view_angle__angle_variant="frontal")
    )


def sample_angle(sample):
    source = sample.dataset_video if sample.dataset_video_id else sample.dataset
    return source.view_angle.angle_variant if source.view_angle_id else None


def require_frontal_annotation(sample):
    if sample_angle(sample) != "frontal":
        raise ValidationError({"knee_annotation": "Knee annotation requires a frontal sample."})
