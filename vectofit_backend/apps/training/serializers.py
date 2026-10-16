from rest_framework import serializers
from apps.analytics.services.features import AVAILABLE_FEATURES, FEATURE_ORDER
from .models import ModelRegistry, TrainingJob

class TrainingJobSerializer(serializers.ModelSerializer):

    dataset_ids = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True, source="datasets"
    )
    dataset_names = serializers.SerializerMethodField()
    has_artifact = serializers.SerializerMethodField()
    artifact_url = serializers.SerializerMethodField()

    class Meta:
        model = TrainingJob
        fields = [
            "id",
            "dataset_ids",
            "dataset_names",
            "algorithm",
            "feature_selection",
            "hyperparameters",
            "random_seed",
            "split_strategy",
            "status",
            "error_message",
            "created_at",
            "started_at",
            "completed_at",
            "sample_count",
            "train_count",
            "test_count",
            "metrics",
            "feature_warnings",
            "has_artifact",
            "artifact_url",
        ]
        read_only_fields = fields

    def get_dataset_names(self, obj):
        return [dataset.name for dataset in obj.datasets.all()]

    def get_has_artifact(self, obj):
        return bool(obj.model_artifact)

    def get_artifact_url(self, obj):
        if not obj.model_artifact:
            return None
        request = self.context.get("request")
        url = obj.model_artifact.url
        return request.build_absolute_uri(url) if request else url

class TrainingJobRequestSerializer(serializers.Serializer):
    dataset_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        help_text="Primary keys of the Datasets to train on.",
    )
    algorithm = serializers.ChoiceField(
        choices=TrainingJob.Algorithm.choices,
        default=TrainingJob.Algorithm.XGBOOST,
    )
    feature_selection = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
        required=False,
        help_text=(
            f"Feature names to use. Empty/omitted means all of {FEATURE_ORDER}. "
            f"Accepted aliases: {AVAILABLE_FEATURES}."
        ),
    )
    hyperparameters = serializers.DictField(required=False, default=dict)
    test_size = serializers.FloatField(
        required=False, default=0.3, min_value=0.1, max_value=0.5
    )
    random_seed = serializers.IntegerField(required=False, default=42)

    def validate_dataset_ids(self, value):
        from apps.datasets.models import Dataset

        requested = list(dict.fromkeys(value))
        existing = set(Dataset.objects.filter(pk__in=requested).values_list("id", flat=True))
        missing = [pk for pk in requested if pk not in existing]
        if missing:
            raise serializers.ValidationError(
                f"Unknown dataset id(s): {missing}."
            )
        return requested

    def validate_feature_selection(self, value):
        from apps.analytics.services.features import FeatureExtractionError, validate_features

        if not value:
            return list(FEATURE_ORDER)
        try:
            return validate_features(value)
        except FeatureExtractionError as exc:
            raise serializers.ValidationError(str(exc)) from exc

class ModelRegistrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelRegistry
        fields = [
            "id",
            "name",
            "version",
            "training_job",
            "algorithm",
            "metrics",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields

class ModelStateSerializer(serializers.ModelSerializer):
    artifact_available = serializers.SerializerMethodField()
    training = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()
    evaluation = serializers.SerializerMethodField()
    feature_warnings = serializers.SerializerMethodField()

    class Meta:
            model = ModelRegistry
            fields = [
                "id",
                "name",
                "version",
                "algorithm",
                "is_active",
                "created_at",
                "artifact_available",
                "training",
                "features",
                "evaluation",
                "feature_warnings",
            ]
            read_only_fields = fields

    @staticmethod
    def _metric(metrics, key):
        value = metrics.get(key)

        return (
            float(value)
            if isinstance(value, (int, float))
            else None
        )

    def get_artifact_available(self, obj):
        return bool(
            obj.artifact
            or obj.training_job.model_artifact
        )

    def get_training(self, obj):
        job = obj.training_job

        return {
            "job_id": job.id,
            "status": job.status,
            "dataset_names": [
                dataset.name
                for dataset in job.datasets.all()
            ],
            "sample_count": job.sample_count,
            "train_count": job.train_count,
            "test_count": job.test_count,
            "split_strategy": job.split_strategy,
            "random_seed": job.random_seed,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
        }

    def get_features(self, obj):
        metrics = (
            obj.training_job.metrics
            or obj.metrics
            or {}
        )

        selected = (
            obj.training_job.feature_selection
            or metrics.get("feature_names")
            or []
        )

        importances = (
            metrics.get("feature_importances")
            or {}
        )

        return {
            "selected": list(selected),
            "importances": {
                str(name): float(value)
                for name, value in importances.items()
                if isinstance(value, (int, float))
            },
        }

    def get_evaluation(self, obj):
        metrics = (
            obj.training_job.metrics
            or obj.metrics
            or {}
        )

        confusion_matrix = (
            metrics.get("confusion_matrix")
            or [[], []]
        )

        return {
            "accuracy": self._metric(
                metrics,
                "accuracy",
            ),
            "balanced_accuracy": self._metric(
                metrics,
                "balanced_accuracy",
            ),
            "precision": self._metric(
                metrics,
                "precision",
            ),
            "recall": self._metric(
                metrics,
                "recall",
            ),
            "f1": self._metric(
                metrics,
                "f1",
            ),
            "confusion_matrix": confusion_matrix,
            "overall_class_distribution": (
                metrics.get(
                    "overall_class_distribution"
                )
                or {}
            ),
            "train_class_distribution": (
                metrics.get(
                    "train_class_distribution"
                )
                or {}
            ),
            "test_class_distribution": (
                metrics.get(
                    "test_class_distribution"
                )
                or {}
            ),
        }

    def get_feature_warnings(self, obj):
        return list(
            obj.training_job.feature_warnings
            or []
        )