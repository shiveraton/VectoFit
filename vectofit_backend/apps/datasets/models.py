import uuid
from pathlib import PurePosixPath
from typing import ClassVar

from django.db import models
from django.db.models import Q

from .storage import dataset_video_storage


def dataset_upload_to(instance, filename):
    safe_name = PurePosixPath(filename.replace("\\", "/")).name
    return f"dataset_videos/dataset_{instance.dataset_id}{uuid.uuid4().hex}_{safe_name}"


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

    video_file = models.FileField(upload_to="datasets/videos/", storage=dataset_video_storage, null=True, blank=True)

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

    def __str__(self):
        return self.name


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

    annotated_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        label = "unlabelled" if self.is_correct is None else str(self.is_correct)
        return f"DatasetSample(dataset={self.dataset_id}, label={label})"


class DatasetAnnotatorAssignment(models.Model):
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="annotator_assignments",
    )
    annotator = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="dataset_assignments",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(
        default=True,
        help_text="Untick to revoke access without deleting the assignment or ratings.",
    )

    def clean(self):
        from django.core.exceptions import ValidationError

        super().clean()
        if self.annotator_id and self.is_active:
            user = self.annotator
            if (
                not user.is_active or user.is_staff or user.is_superuser
                or not getattr(getattr(user, "profile", None), "is_annotator", False)
            ):
                raise ValidationError({"annotator": "Choose an active, non-staff annotator."})

    class Meta:
        unique_together = ("dataset", "annotator")
        ordering: ClassVar[list] = ["-assigned_at"]

    def __str__(self):
        return f"Dataset {self.dataset_id} assigned to {self.annotator.username}"


class DatasetAssignmentEvent(models.Model):
    class Action(models.TextChoices):
        GRANTED = "granted", "Granted"
        REVOKED = "revoked", "Revoked"

    assignment = models.ForeignKey(
        DatasetAnnotatorAssignment, on_delete=models.CASCADE, related_name="events",
    )
    actor = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, related_name="dataset_assignment_events",
    )
    action = models.CharField(max_length=12, choices=Action.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar[list] = ["-created_at", "-id"]


class KneeAnnotation(models.Model):
    sample = models.ForeignKey(
        DatasetSample,
        on_delete=models.CASCADE,
        related_name="knee_annotation_records",
    )
    annotation = models.JSONField(null=True, blank=True)
    annotator = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="knee_annotations",
    )
    rubric_version = models.CharField(max_length=32, default="knee_v1")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=["sample"],
                condition=Q(annotator__isnull=True),
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

    video_file = models.FileField(upload_to="dataset_video_upload_to", storage=dataset_video_storage)

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
