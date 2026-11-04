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


def final_knee_target(sample):
    latest_by_annotator = _latest_by_annotator(sample)
    targets = {
        knee_target(record.annotation)
        for record in latest_by_annotator.values()
        if record.annotation is not None
    }
    if not targets:
        return None
    if len(targets) > 1:
        return "disputed"
    return targets.pop()


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
