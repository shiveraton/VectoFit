from typing import Mapping

def knee_target(annotation: Mapping[str, Mapping[str, str | None]]) -> str:
    grades = [annotation[side].get("grade") for side in ("left", "right")]
    if "deviated" in grades:
        return "bad"
    if "unassessable" in grades:
        return "unassessable"
    if "borderline" in grades:
        return "borderline"
    return "good"


def knee_label_evidence(sample):
    records = list(_latest_by_annotator(sample).values())
    targets = {
        knee_target(record.annotation)
        for record in records
        if record.annotation is not None
    }
    target = None
    if len(targets) > 1:
        target = "disputed"
    elif targets:
        target = targets.pop()
    return {
        "target": target,
        "annotations": [
            {
                "id": record.pk,
                "annotator_id": record.annotator_id,
                "created_at": record.created_at.isoformat(),
                "annotation": record.annotation,
                "rubric_version": record.rubric_version,
            }
            for record in records
        ],
    }


def final_knee_target(sample):
    return knee_label_evidence(sample)["target"]


def _latest_by_annotator(sample):
    latest_by_annotator = {}
    records = sample.knee_annotation_records.select_related("annotator")
    for record in records.order_by("annotator_id", "-created_at", "-id"):
        if record.annotator_id not in latest_by_annotator:
            latest_by_annotator[record.annotator_id] = record
    return latest_by_annotator


def latest_annotator_ids(sample):
    return [
        annotator_id
        for annotator_id in _latest_by_annotator(sample)
        if annotator_id is not None
    ]
