from collections import Counter, defaultdict

from apps.datasets.models import Dataset, DatasetSample, DatasetVideo

DATASET_ID = 17

dataset = Dataset.objects.get(pk=DATASET_ID)
videos = DatasetVideo.objects.filter(dataset=dataset).select_related(
    "participant", "view_angle"
)
samples = DatasetSample.objects.filter(dataset=dataset).select_related(
    "dataset_video",
    "dataset_video__participant",
    "dataset_video__view_angle",
    "rep_assessment",
)

print(f"\nDATASET: {dataset.name} (ID={dataset.id})")
print("=" * 70)

# 1. Video inventory
print("\n1. VIDEO INVENTORY")
print("Total videos:", videos.count())
print("By camera angle:")
for angle, count in (
    videos.values_list("view_angle__angle_variant")
    .order_by("view_angle__angle_variant")
    .annotate_count()
    if False
    else []
):
    print(angle, count)

video_counts = Counter(videos.values_list("view_angle__angle_variant", flat=True))
for angle, count in sorted(video_counts.items(), key=lambda x: str(x[0])):
    print(f"  {angle}: {count}")

print("\nVideos by processing status:")
for row in videos.values("status").order_by("status").distinct():
    status = row["status"]
    print(f"  {status}: {videos.filter(status=status).count()}")

# 2. Participant coverage
print("\n2. PARTICIPANT COVERAGE")
participant_videos = defaultdict(list)
for video in videos:
    participant_videos[video.participant.participant_code].append(video)

print("Unique participants in videos:", len(participant_videos))
for participant, rows in sorted(participant_videos.items()):
    angles = Counter(v.view_angle.angle_variant for v in rows)
    print(
        f"  {participant}: {len(rows)} videos; "
        + ", ".join(f"{k}={v}" for k, v in sorted(angles.items()))
    )

# 3. Repetition labels
print("\n3. REPETITION LABELS")
label_counts = Counter(
    "UNLABELLED" if s.is_correct is None else "GOOD" if s.is_correct else "BAD"
    for s in samples
)
print("Total DatasetSample records:", samples.count())
for label in ("GOOD", "BAD", "UNLABELLED"):
    print(f"  {label}: {label_counts[label]}")

print("\nLabels by camera angle:")
by_angle_label = Counter()
for sample in samples:
    angle = (
        sample.dataset_video.view_angle.angle_variant
        if sample.dataset_video_id and sample.dataset_video.view_angle_id
        else "UNKNOWN"
    )
    label = (
        "UNLABELLED"
        if sample.is_correct is None
        else "GOOD"
        if sample.is_correct
        else "BAD"
    )
    by_angle_label[(angle, label)] += 1

for (angle, label), count in sorted(
    by_angle_label.items(), key=lambda x: (str(x[0][0]), x[0][1])
):
    print(f"  {angle} / {label}: {count}")

# 4. Repetitions per participant
print("\n4. REPETITIONS PER PARTICIPANT")
participant_reps = Counter()
participant_labels = defaultdict(Counter)

for sample in samples:
    if sample.dataset_video_id:
        participant = sample.dataset_video.participant.participant_code
    else:
        participant = "UNKNOWN (legacy sample)"

    participant_reps[participant] += 1
    label = (
        "UNLABELLED"
        if sample.is_correct is None
        else "GOOD"
        if sample.is_correct
        else "BAD"
    )
    participant_labels[participant][label] += 1

for participant in sorted(participant_reps):
    labels = participant_labels[participant]
    print(
        f"  {participant}: {participant_reps[participant]} reps | "
        f"GOOD={labels['GOOD']}, BAD={labels['BAD']}, "
        f"UNLABELLED={labels['UNLABELLED']}"
    )

print("\nParticipants with both GOOD and BAD labels:")
both = [
    p
    for p, labels in participant_labels.items()
    if labels["GOOD"] > 0 and labels["BAD"] > 0
]
print(len(both), "of", len(participant_labels))
print(", ".join(sorted(both)) or "(none)")

# 5. Landmark availability and basic structural checks
print("\n5. LANDMARK AVAILABILITY")
landmark_counts = Counter()
empty_examples = []

for sample in samples:
    rep = sample.rep_assessment
    series = rep.landmark_series if rep else None

    if not isinstance(series, list) or not series:
        landmark_counts["EMPTY_OR_MISSING"] += 1
        if len(empty_examples) < 10:
            empty_examples.append(sample.id)
        continue

    landmark_counts["NONEMPTY_SERIES"] += 1

    valid_frames = 0
    for frame in series:
        if isinstance(frame, dict) and frame or isinstance(frame, list) and frame:
            valid_frames += 1

    landmark_counts["FRAMES_WITH_LANDMARK_DATA"] += valid_frames
    landmark_counts["SERIES_LENGTH_TOTAL"] += len(series)

print("Samples with nonempty landmark series:", landmark_counts["NONEMPTY_SERIES"])
print("Samples with missing/empty series:", landmark_counts["EMPTY_OR_MISSING"])
print("Total frames across nonempty series:", landmark_counts["SERIES_LENGTH_TOTAL"])
print(
    "Frames with nonempty landmark structures:",
    landmark_counts["FRAMES_WITH_LANDMARK_DATA"],
)
print("Sample IDs with missing series (first 10):", empty_examples)

# 6. Legacy/orphan relationships
print("\n6. PROVENANCE GAPS")
print(
    "Samples without DatasetVideo:", samples.filter(dataset_video__isnull=True).count()
)
print("Samples without annotator:", samples.filter(annotator__isnull=True).count())
print(
    "Samples with annotated_at missing:",
    samples.filter(annotated_at__isnull=True).count(),
)
print("Samples with blank error_label:", samples.filter(error_label="").count())

print("\nAudit complete. No records were modified.")
