import uuid
from pathlib import PurePosixPath
from typing import ClassVar

from django.db import models
from django.conf import settings
from django.db.models import Exists, OuterRef, Q


def dataset_upload_to(instance, filename):
    safe_name = PurePosixPath(filename.replace("\\", "/")).name
    return (
        f"dataset_videos/dataset_{instance.dataset_id}/{uuid.uuid4().hex}_{safe_name}"
    )


class Participant(models.Model):
    participant_code = models.CharField(
        max_length=32,
        unique=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar[list] = ["participant_code"]


class ViewAngle(models.Model):
    ANGLE_CHOICES: ClassVar[list] = [
        ("diagonal", "Diagonal"),
        ("frontal", "Frontal"),
        ("sagittal", "Sagittal"),
    ]

    angle_variant = models.CharField(
        max_length=20,
        unique=True,
        choices=ANGLE_CHOICES,
    )

    def __str__(self):
        return self.get_angle_variant_display()


class Dataset(models.Model):
    class ReviewPolicy(models.TextChoices):
        SOURCE = "source", "Use source labels"
        ALL = "all", "Review all videos"
        SUBSET = "subset", "Review selected videos"

    class SelectionMethod(models.TextChoices):
        STRATIFIED = "stratified", "Stratified"
        MANUAL = "manual", "Manual"

    PURPOSE_CHOICES: ClassVar[list] = [
        ("training", "Training"),
        ("evaluation", "Evaluation"),
    ]

    EXERCISE_CHOICES: ClassVar[list] = [
        ("bodyweight_squat", "Bodyweight Squat"),
        ("goblet_squat", "Goblet Squat"),
    ]

    name = models.CharField(max_length=50)

    description = models.TextField(blank=True)

    exercise_type = models.CharField(max_length=50, choices=EXERCISE_CHOICES)

    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)

    primary_target = models.CharField(max_length=50, default="biomechanical_errors")

    secondary_target = models.CharField(max_length=50, default="biomechanical_errors")

    status = models.CharField(max_length=20, default="PENDING")

    error_message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    participant = models.ForeignKey(
        Participant,
        on_delete=models.PROTECT,
        related_name="datasets",
        null=True,
        blank=True,
        help_text="Research participant represented by this dataset.",
    )

    view_angle = models.ForeignKey(
        ViewAngle,
        on_delete=models.RESTRICT,
        related_name="datasets",
        null=True,
        blank=True,
        help_text="Camera view used to capture this dataset.",
    )

    video_file = models.FileField(upload_to="datasets/videos/", null=True, blank=True)

    review_policy = models.CharField(
        max_length=12,
        choices=ReviewPolicy.choices,
        default=ReviewPolicy.SOURCE,
    )
    selection_method = models.CharField(
        max_length=12,
        choices=SelectionMethod.choices,
        default=SelectionMethod.STRATIFIED,
    )
    review_count = models.PositiveIntegerField(null=True, blank=True)
    random_seed = models.IntegerField(null=True, blank=True)
    selected_video_paths = models.JSONField(default=list, blank=True)
    pipeline_config_hash = models.CharField(max_length=64, blank=True, default="")

    def __str__(self):
        return self.name


class DatasetSampleQuerySet(models.QuerySet):
    def annotate_annotation_status(self):
        return self.annotate(
            _has_knee_annotation=Exists(
                KneeAnnotation.objects.filter(sample=OuterRef("pk"))
            ),
            _has_legacy_label=Q(is_correct__isnull=False) | ~Q(error_label=""),
        )


class DatasetSample(models.Model):
    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="samples"
    )

    dataset_video = models.ForeignKey(
        "DatasetVideo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="samples",
    )

    rep_assessment = models.ForeignKey(
        "assessments.RepAssessment",
        on_delete=models.CASCADE,
        related_name="dataset_sample",
    )

    is_correct = models.BooleanField(
        null=True,
        blank=True,
        help_text=(
            "Coarse ground-truth label for this repetition. NULL means "
            "unlabelled, and unlabelled repetitions are excluded from training."
        ),
    )

    error_label = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional semantic error class, e.g. 'knee_valgus', 'shallow_depth'.",
    )

    annotator = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="annotated_dataset_samples",
        help_text="Who assigned the label.",
    )

    objects = DatasetSampleQuerySet.as_manager()

    annotated_at = models.DateTimeField(null=True, blank=True)

    label_source = models.CharField(max_length=16, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def has_knee_annotation(self):
        return self.knee_annotations.exists()

    @property
    def has_legacy_label(self):
        return self.is_correct is not None or bool(self.error_label)

    @property
    def is_manually_annotated(self):
        return self.has_knee_annotation or self.has_legacy_label

    @property
    def annotation_source(self):
        has_knee = self.has_knee_annotation
        has_legacy = self.has_legacy_label

        if has_knee and has_legacy:
            return "both"
        elif has_knee:
            return "knee_annotation"
        elif has_legacy:
            return "legacy"
        return "unannotated"

    def __str__(self):
        label = "unlabelled" if self.is_correct is None else str(self.is_correct)
        return f"DatasetSample(dataset={self.dataset_id}, label={label})"


class KneeAnnotation(models.Model):
    sample = models.ForeignKey(
        DatasetSample, on_delete=models.CASCADE, related_name="knee_annotations"
    )
    annotator = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knee_annotations",
    )
    annotation = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=["sample", "annotator"],
                name="unique_knee_annotation_per_annotator",
            ),
            models.UniqueConstraint(
                fields=["sample"],
                condition=models.Q(annotator__isnull=True),
                name="unique_unowned_knee_annotation_per_sample",
            ),
        ]

    def __str__(self):
        return f"KneeAnnotation(sample={self.sample_id})"


class DatasetVideo(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        READY = "READY", "Ready"
        FAILED = "FAILED", "Failed"

    dataset = models.ForeignKey(
        Dataset, on_delete=models.CASCADE, related_name="videos"
    )

    participant = models.ForeignKey(
        Participant, on_delete=models.PROTECT, related_name="dataset_videos"
    )

    view_angle = models.ForeignKey(
        ViewAngle, on_delete=models.RESTRICT, related_name="dataset_videos"
    )

    video_file = models.FileField(upload_to=dataset_upload_to)

    source_label = models.BooleanField(
        null=True,
        blank=True,
        help_text=(
            "Optional label inherited from the source folder. "
            "When present, this label is applied to extracted repetitions."
        ),
    )

    source_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Relative filename inside the imported ZIP archive.",
    )

    requires_manual_review = models.BooleanField(
        default=False,
        help_text="Whether repetitions from this video must be manually labelled.",
    )

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering: ClassVar[list] = ["participant__participant_code", "view_angle"]

        indexes: ClassVar[list] = [
            models.Index(fields=["dataset", "status"]),
            models.Index(fields=["participant", "view_angle"]),
        ]

    def __str__(self):
        label = (
            "GOOD"
            if self.source_label is True
            else "BAD"
            if self.source_label is False
            else "UNLABELLED"
        )
        return (
            f"{self.dataset.name} / "
            f"{self.participant.participant_code} / "
            f"{self.view_angle.angle_variant} / {label}"
        )


class AnnotationEventQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Annotation events are immutable.")

    def delete(self):
        raise TypeError("Annotation events are immutable.")


class AnnotationEvent(models.Model):
    class Action(models.TextChoices):
        SAVE = "save", "Save"
        CLEAR = "clear", "Clear"
        RESOLVE = "resolve", "Resolve"
        ADJUDICATE = "adjudicate", "Adjudicate"
        REASSIGN = "reassign", "Reassign"

    sample = models.ForeignKey(
        DatasetSample, on_delete=models.CASCADE, related_name="annotation_events"
    )
    annotator = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    entered_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, related_name="+"
    )
    action = models.CharField(max_length=16, choices=Action.choices)
    target_label = models.CharField(max_length=32, blank=True)
    payload = models.JSONField(null=True, blank=True)
    rubric_version = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    objects: ClassVar[models.Manager] = AnnotationEventQuerySet.as_manager()

    class Meta:
        indexes: ClassVar[list] = [
            models.Index(fields=["sample", "created_at"]),
            models.Index(fields=["annotator", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise TypeError("Annotation events are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Annotation events are immutable.")

class DatasetAnnotatorAssignment(models.Model):
    dataset = models.ForeignKey(
        "datasets.Dataset",
        on_delete=models.CASCADE,
        related_name="annotator_assignments",
    )
    annotator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dataset_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("dataset", "annotator")
