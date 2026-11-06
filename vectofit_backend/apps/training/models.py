from typing import ClassVar

from django.db import models


class TrainingJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    class Algorithm(models.TextChoices):
        XGBOOST = "xgboost", "XGBoost"

    class PredictionTarget(models.TextChoices):
        BINARY_FORM = "binary_form", "Correct vs incorrect form"
        ERROR_TYPE = "error_type", "Correct form vs specific error type"
        KNEE_ALIGNMENT = "knee_alignment", "Frontal-plane knee alignment"

    VIEW_ANGLE_CHOICES: ClassVar[list] = [
        ("", "Legacy/unspecified"),
        ("diagonal", "Diagonal"),
        ("frontal", "Frontal"),
        ("sagittal", "Sagittal"),
    ]

    datasets = models.ManyToManyField(
        "datasets.Dataset",
        related_name="training_jobs",
        help_text="Datasets selected for this run.",
    )

    algorithm = models.CharField(
        max_length=32,
        choices=Algorithm.choices,
        default=Algorithm.XGBOOST,
    )

    view_angle = models.CharField(
        max_length=20,
        choices=VIEW_ANGLE_CHOICES,
        blank=True,
        default="",
        help_text="Camera angle selected for this model run.",
    )

    prediction_target = models.CharField(
        max_length=24,
        choices=PredictionTarget.choices,
        default=PredictionTarget.BINARY_FORM,
        help_text=(
            "binary_form predicts correct/incorrect. error_type predicts "
            "correct_form vs a manually assigned error_label."
        ),
    )

    feature_schema_version = models.CharField(
        max_length=48,
        default="python_rep_features_v2",
        help_text="Version of the numerical feature definitions used by this run.",
    )

    training_manifest = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Audible training manifest: exact sample IDs, target labels, "
            "participant groups, and train/test assignments."
        ),
    )

    feature_selection = models.JSONField(
        default=list,
        help_text="Ordered feature columns fed to the model.",
    )

    hyperparameters = models.JSONField(
        default=dict,
        help_text="Hyperparameters actually used, after defaults are applied.",
    )

    random_seed = models.IntegerField(
        default=42,
        help_text="Seed for the train/test split and model initialization.",
    )

    test_size = models.FloatField(
        default=0.3,
        help_text="Requested fraction of participant groups reserved for held-out testing.",
    )

    split_strategy = models.CharField(
        max_length=32,
        default="group_by_participant",
        help_text=(
            "How the held-out test set was formed. 'group_by_participant' keeps "
            "all repetitions from the same research participant on one side of "
            "the split to avoid subject-level data leakage."
        ),
    )

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    sample_count = models.PositiveIntegerField(
        default=0, help_text="Total ML samples (repetitions) available."
    )
    train_count = models.PositiveIntegerField(default=0)
    test_count = models.PositiveIntegerField(default=0)

    metrics = models.JSONField(
        default=dict,
        help_text="Held-out evaluation metrics, plus class distribution info.",
    )

    feature_warnings = models.JSONField(
        default=list,
        help_text="Scientific caveats recorded during feature extraction.",
    )

    model_artifact = models.FileField(
        upload_to="training_artifacts/",
        null=True,
        blank=True,
        help_text="Serialised estimator produced by this run.",
    )

    class Meta:
        ordering: ClassVar[list] = ["-created_at"]

    def __str__(self):
        return f"TrainingJob #{self.pk} ({self.algorithm}, {self.status})"


class ModelRegistry(models.Model):
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=32, default="1.0")
    training_job = models.ForeignKey(
        TrainingJob,
        on_delete=models.CASCADE,
        related_name="registry_entries",
    )
    algorithm = models.CharField(max_length=32, choices=TrainingJob.Algorithm.choices)
    artifact = models.FileField(upload_to="model_registry/")
    metrics = models.JSONField(default=dict)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering: ClassVar[list] = ["-created_at"]
        unique_together = ("name", "version")

    def __str__(self):
        return f"{self.name} v{self.version} ({self.algorithm})"
