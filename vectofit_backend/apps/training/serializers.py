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