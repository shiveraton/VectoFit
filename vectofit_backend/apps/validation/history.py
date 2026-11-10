from apps.datasets.models import KneeAnnotation
from .models import ValidationAnnotationEvent


def annotation_history(repetition_id):
    return [
        {"id": row.pk, "source": "annotation", "created_at": row.created_at,
         "user_id": row.annotator_id, "payload": row.annotation}
        for row in KneeAnnotation.objects.filter(sample_id=repetition_id).order_by("created_at", "pk")
    ]


def validation_history(repetition_id):
    return [
        {"id": row.pk, "source": row.source, "created_at": row.created_at,
         "user_id": row.payload["validator_id"], "payload": row.payload}
        for row in ValidationAnnotationEvent.objects.filter(annotation__repetition_id=repetition_id)
    ]


HISTORY_SOURCES = {"annotation": annotation_history, "validation": validation_history}


def history_for(repetition_id, source):
    return HISTORY_SOURCES[source](repetition_id)
