from collections import Counter, defaultdict

from apps.datasets.models import Dataset, DatasetSample

DATASET_ID = 17

dataset = Dataset.objects.get(pk=DATASET_ID)

samples = list(
    DatasetSample.objects.filter(dataset_id=DATASET_ID).select_related(
        "dataset_video__participant",
        "dataset_video__view_angle",
        "rep_assessment",
        "annotator",
    )
)


def label_name(value):
    if value is True:
        return "GOOD"
    if value is False:
        return "BAD"
    return "UNLABELLED"


frontal = [
    s
    for s in samples
    if s.dataset_video and s.dataset_video.view_angle.angle_variant == "frontal"
]

print(f"DATASET: {dataset.name} (ID={dataset.id})")
print(f"FRONTAL SAMPLES: {len(frontal)}")

print("\n1. LABEL ORIGIN AND REVIEW STATUS")

summary = Counter()
by_source_and_review = Counter()
participant_labels = defaultdict(Counter)
issues = []

for s in frontal:
    video = s.dataset_video
    source = video.source_label
    current = s.is_correct

    source_name = label_name(source)
    current_name = label_name(current)

    summary[f"current_{current_name}"] += 1
    summary[f"source_{source_name}"] += 1

    review_status = (
        "REQUIRES_REVIEW" if video.requires_manual_review else "NOT_FLAGGED_FOR_REVIEW"
    )

    by_source_and_review[source_name, review_status, current_name] += 1

    participant = video.participant.participant_code
    participant_labels[participant][current_name] += 1

    if source is None:
        comparison = "NO_SOURCE_LABEL"
    elif current is None:
        comparison = "CURRENT_LABEL_MISSING"
    elif current == source:
        comparison = "MATCHES_SOURCE_LABEL"
    else:
        comparison = "DIFFERS_FROM_SOURCE_LABEL"

    summary[comparison] += 1

    if (
        not s.annotator_id
        or not s.annotated_at
        or (current is False and not s.error_label.strip())
    ):
        summary["POTENTIAL_PROVENANCE_GAP"] += 1

    if (
        comparison != "MATCHES_SOURCE_LABEL"
        or not s.annotator_id
        or not s.annotated_at
        or (current is False and not s.error_label.strip())
    ):
        issues.append(
            {
                "sample_id": s.id,
                "participant": participant,
                "source_path": video.source_path,
                "source_label": source_name,
                "current_label": current_name,
                "requires_manual_review": video.requires_manual_review,
                "annotator": (s.annotator.get_username() if s.annotator_id else None),
                "annotated_at": str(s.annotated_at),
                "error_label": s.error_label,
                "comparison": comparison,
            }
        )

print("\nCOUNTS")
for key, value in sorted(summary.items()):
    print(f"  {key}: {value}")

print("\n2. SOURCE LABEL / REVIEW FLAG / CURRENT LABEL")
for key, count in sorted(by_source_and_review.items()):
    source, review, current = key
    print(f"  source={source} | {review} | current={current}: {count}")

print("\n3. PARTICIPANT LABELS")
for participant, counts in sorted(participant_labels.items()):
    print(f"  {participant}: {dict(counts)}")

print("\n4. POTENTIAL ISSUES (first 30)")
for issue in issues[:30]:
    print(issue)

print(f"\nTotal potential issue records: {len(issues)}")
print("Audit complete. No records were modified.")
