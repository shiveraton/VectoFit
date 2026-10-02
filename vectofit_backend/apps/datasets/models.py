from django.db import models
from django.utils import timezone

class Dataset(models.Model):
    PURPOSE_CHOICES = [
        ("training", "Training"),
        ("evaluation", "Evaluation"),
    ]

    EXERCISE_CHOICES = [
        ("bodyweight_squat", "Bodyweight Squat"),
        ("goblet_squat", "Goblet Squat"),
    ]

    name = models.CharField(max_length=50)

    description = models.TextField(
        blank=True
    )

    exercise_type = models.CharField(
        max_length=50,
        choices=EXERCISE_CHOICES
    )

    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES
    )

    primary_target = models.CharField(
        max_length=50,
        default="biomechanical_errors"
    )

    secondary_target = models.CharField(
        max_length=50,
        default="biomechanical_errors"
    )

    status = models.CharField(
        max_length=20,
        default='PENDING'
    )

    error_message = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now = True
    )

    video_file = models.FileField(upload_to='datasets/videos/', null=True, blank=True)
    status = models.CharField(max_length=20, default='PENDING')

class DatasetSample(models.Model):
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name="samples"
    )

    rep_assessment = models.ForeignKey(
        "assessments.RepAssessment",
        on_delete=models.CASCADE,
        related_name="dataset_sample"
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
        max_length=50,
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
    
    annotated_at = models.DateTimeField(default=timezone.now)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        label = "unlabelled" if self.is_correct is None else str(self.is_correct)
        return f"DatasetSample(dataset={self.dataset_id}, label={label})"

def __str__(self):
    return self.name