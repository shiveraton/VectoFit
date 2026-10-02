from django.db import models

class TrainingJob(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    class Algorithm(models.TextChoices):
        XGBOOST = "xgboost", "XGBoost"

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
        help_text="Seed for the train/test split and model initialisation.",
    )

    split_strategy = models.CharField(
        max_length=32,
        default="group_by_dataset",
        help_text=(
            "How the held-out test set was formed. 'group_by_dataset' keeps all "
            "repetitions from the same source dataset on one side of the split "
            "to avoid leaking correlated samples."
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
        ordering = ["-created_at"]

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
    algorithm = models.CharField(
        max_length=32, choices=TrainingJob.Algorithm.choices
    )
    artifact = models.FileField(upload_to="model_registry/")
    metrics = models.JSONField(default=dict)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("name", "version")

    def __str__(self):
        return f"{self.name} v{self.version} ({self.algorithm})"
