import math
from typing import ClassVar

from rest_framework import serializers

from apps.analytics.services.features import (
    FeatureExtractionError,
    validate_features,
)

from .models import ModelRegistry, TrainingJob


class TrainingJobSerializer(serializers.ModelSerializer):
    dataset_ids = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True, source="datasets"
    )
    dataset_names = serializers.SerializerMethodField()
    has_artifact = serializers.SerializerMethodField()
    artifact_url = serializers.SerializerMethodField()
    training_manifest_summary = serializers.SerializerMethodField()

    class Meta:
        model = TrainingJob
        fields: ClassVar[list] = [
            "id",
            "dataset_ids",
            "dataset_names",
            "algorithm",
            "view_angle",
            "prediction_target",
            "feature_schema_version",
            "training_manifest_summary",
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

    def get_training_manifest_summary(self, obj):
        manifest = obj.training_manifest or {}
        samples = manifest.get("samples", [])
        train_ids = manifest.get("train_sample_ids", [])
        test_ids = manifest.get("test_sample_ids", [])
        return {
            "manifest_version": manifest.get("manifest_version"),
            "sample_count": len(samples),
            "train_sample_count": len(train_ids),
            "test_sample_count": len(test_ids),
            "class_mapping": manifest.get("class_mapping", {}),
            "feature_schema_version": manifest.get(
                "feature_schema_version", obj.feature_schema_version
            ),
            "manifest_sha256": manifest.get("manifest_sha256"),
            "view_angle": manifest.get("view_angle", obj.view_angle),
            "prediction_target": manifest.get(
                "prediction_target", obj.prediction_target
            ),
            "model_version": manifest.get("model_version"),
            "split_strategy": manifest.get("split_strategy", obj.split_strategy),
            "exclusion_counts": manifest.get("exclusion_counts", {}),
        }

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
    view_angle = serializers.ChoiceField(
        choices=[
            ("diagonal", "Diagonal"),
            ("frontal", "Frontal"),
            ("sagittal", "Sagittal"),
        ],
        required=True,
    )
    prediction_target = serializers.ChoiceField(
        choices=TrainingJob.PredictionTarget.choices,
        default=TrainingJob.PredictionTarget.BINARY_FORM,
    )
    model_version = serializers.ChoiceField(
        choices=[("M0", "M0 (FPPA only)"), ("M1", "M1 (FPPA + bilateral asymmetry)")],
        default="M1",
        help_text="Feature set: M0 = 4 FPPA features, M1 = M0 + 2 asymmetry features.",
    )
    evaluation = serializers.ChoiceField(
        choices=[
            ("lopo", "Leave-one-participant-out"),
            ("holdout", "Single participant-grouped holdout"),
        ],
        default="lopo",
    )
    feature_selection = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
        required=False,
        help_text=(
            "Feature names to use. Empty/omitted means every feature of the "
            "selected model_version."
        ),
    )
    hyperparameters = serializers.DictField(required=False, default=dict)
    test_size = serializers.FloatField(
        required=False, default=0.3, min_value=0.1, max_value=0.5
    )
    random_seed = serializers.IntegerField(required=False, default=42)

    def validate_hyperparameters(self, value):
        from .services.trainer import BASELINE_HYPERPARAMETERS

        editable_parameters = {
            name
            for name, default in BASELINE_HYPERPARAMETERS.items()
            if isinstance(default, (int, float)) and not isinstance(default, bool)
        }
        unknown = sorted(set(value) - editable_parameters)
        if unknown:
            raise serializers.ValidationError(
                f"Unsupported or fixed hyperparameter(s): {unknown}. "
                f"Editable numeric parameters: {sorted(editable_parameters)}"
            )

        for name, raw in value.items():
            if (
                isinstance(raw, bool)
                or not isinstance(raw, (int, float))
                or not math.isfinite(float(raw))
            ):
                raise serializers.ValidationError(
                    {name: "Value must be a finite number."}
                )
            number = float(raw)
            if name in {"n_estimators", "max_depth"} and (
                not number.is_integer() or number < 1
            ):
                raise serializers.ValidationError(
                    {name: "Value must be a positive integer."}
                )
            if name == "learning_rate" and not 0 < number <= 1:
                raise serializers.ValidationError(
                    {name: "Value must be greater than 0 and at most 1."}
                )
            if name in {"subsample", "colsample_bytree"} and not 0 < number <= 1:
                raise serializers.ValidationError(
                    {name: "Value must be greater than 0 and at most 1."}
                )
            if name in {"min_child_weight", "reg_lambda"} and number < 0:
                raise serializers.ValidationError({name: "Value must be non-negative."})

        return value

    def validate_dataset_ids(self, value):
        from apps.datasets.models import Dataset

        requested = list(dict.fromkeys(value))
        existing = set(
            Dataset.objects.filter(pk__in=requested).values_list("id", flat=True)
        )
        missing = [pk for pk in requested if pk not in existing]
        if missing:
            raise serializers.ValidationError(f"Unknown dataset id(s): {missing}.")
        return requested

    def validate(self, attrs):
        from apps.datasets.models import Dataset, DatasetVideo

        dataset_ids = attrs["dataset_ids"]
        angle = attrs["view_angle"]
        target = attrs["prediction_target"]
        try:
            attrs["feature_selection"] = validate_features(
                attrs.get("feature_selection") or None,
                model_version=attrs["model_version"],
            )
        except FeatureExtractionError as exc:
            raise serializers.ValidationError({"feature_selection": str(exc)}) from exc
        datasets = list(
            Dataset.objects.select_related("view_angle")
            .prefetch_related("videos__view_angle")
            .filter(pk__in=dataset_ids)
        )
        by_id = {dataset.pk: dataset for dataset in datasets}
        incompatible = []
        target_classes = set()
        binary_classes = set()
        participant_ids = set()

        for dataset_id in dataset_ids:
            dataset = by_id[dataset_id]
            if dataset.purpose != "training":
                incompatible.append(f"{dataset.name}: purpose must be 'training'")
            if dataset.status != "READY":
                incompatible.append(
                    f"{dataset.name}: status must be READY (currently {dataset.status})"
                )

            ready_angles = set(
                dataset.videos.filter(status=DatasetVideo.Status.READY).values_list(
                    "view_angle__angle_variant", flat=True
                )
            )
            if (
                not dataset.videos.exists()
                and dataset.view_angle_id
                and dataset.view_angle
            ):
                ready_angles.add(dataset.view_angle.angle_variant)
            if angle not in ready_angles:
                incompatible.append(
                    f"{dataset.name}: no READY data for the {angle} camera angle"
                )
                continue

            samples = dataset.samples.filter(is_correct__isnull=False)
            if dataset.videos.exists():
                samples = samples.filter(
                    dataset_video__view_angle__angle_variant=angle,
                    dataset_video__status=DatasetVideo.Status.READY,
                )
            else:
                samples = samples.filter(
                    dataset_video__isnull=True,
                    dataset__view_angle__angle_variant=angle,
                )

            if target == TrainingJob.PredictionTarget.BINARY_FORM:
                present = set(samples.values_list("is_correct", flat=True))
                binary_classes.update(present)
                if not present:
                    incompatible.append(
                        f"{dataset.name}: no labelled samples for {angle}"
                    )
            else:
                for sample in samples.values("is_correct", "error_label"):
                    if sample["is_correct"]:
                        target_classes.add("correct_form")
                    else:
                        error_label = "_".join(
                            (sample["error_label"] or "").strip().casefold().split()
                        )
                        if error_label and error_label != "correct_form":
                            target_classes.add(error_label)

            if dataset.videos.exists():
                participant_ids.update(
                    samples.exclude(
                        dataset_video__participant__isnull=True
                    ).values_list("dataset_video__participant_id", flat=True)
                )
            elif dataset.participant_id:
                participant_ids.add(dataset.participant_id)

        if incompatible:
            raise serializers.ValidationError({"dataset_ids": incompatible})

        if len(participant_ids) < 2:
            raise serializers.ValidationError(
                {
                    "dataset_ids": (
                        "Group by Participant requires at least two distinct participants "
                        "with labelled repetitions. Select datasets containing another "
                        "participant before training."
                    )
                }
            )

        if target == TrainingJob.PredictionTarget.BINARY_FORM and binary_classes != {
            False,
            True,
        }:
            observed = sorted("GOOD" if value else "BAD" for value in binary_classes)
            raise serializers.ValidationError(
                {
                    "prediction_target": (
                        "Binary form training requires both GOOD and BAD labelled samples "
                        f"for the selected camera angle; observed classes: {observed or ['none']}."
                    )
                }
            )

        if (
            target == TrainingJob.PredictionTarget.ERROR_TYPE
            and len(target_classes) < 2
        ):
            raise serializers.ValidationError(
                {
                    "prediction_target": (
                        "Error-type training requires at least two target classes: "
                        "correct_form and one or more populated error_label categories. "
                        "Annotate incorrect repetitions with specific error labels first."
                    )
                }
            )
        return attrs


class ModelPredictionRequestSerializer(serializers.Serializer):
    model_name = serializers.CharField(
        max_length=100, required=False, default="vectofit-squat-classifier"
    )
    view_angle = serializers.ChoiceField(
        choices=[
            ("diagonal", "Diagonal"),
            ("frontal", "Frontal"),
            ("sagittal", "Sagittal"),
        ]
    )
    prediction_target = serializers.ChoiceField(
        choices=TrainingJob.PredictionTarget.choices
    )
    feature_schema_version = serializers.CharField(max_length=48)
    features = serializers.DictField(child=serializers.FloatField(), allow_empty=False)

    def validate_features(self, value):
        invalid = [name for name, number in value.items() if not math.isfinite(number)]
        if invalid:
            raise serializers.ValidationError(
                f"Features must be finite numbers: {invalid}"
            )
        return value


class ModelRegistrySerializer(serializers.ModelSerializer):
    view_angle = serializers.CharField(source="training_job.view_angle", read_only=True)
    prediction_target = serializers.CharField(
        source="training_job.prediction_target", read_only=True
    )
    feature_schema_version = serializers.CharField(
        source="training_job.feature_schema_version", read_only=True
    )

    class Meta:
        model = ModelRegistry
        fields: ClassVar[list] = [
            "id",
            "name",
            "version",
            "training_job",
            "algorithm",
            "view_angle",
            "prediction_target",
            "feature_schema_version",
            "metrics",
            "is_active",
            "created_at",
        ]
        read_only_fields = fields


class ModelStateSerializer(serializers.ModelSerializer):
    view_angle = serializers.CharField(source="training_job.view_angle", read_only=True)
    prediction_target = serializers.CharField(
        source="training_job.prediction_target", read_only=True
    )
    feature_schema_version = serializers.CharField(
        source="training_job.feature_schema_version", read_only=True
    )
    artifact_available = serializers.SerializerMethodField()
    training = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()
    evaluation = serializers.SerializerMethodField()
    feature_warnings = serializers.SerializerMethodField()
    training_manifest = serializers.SerializerMethodField()

    class Meta:
        model = ModelRegistry
        fields: ClassVar[list] = [
            "id",
            "name",
            "version",
            "algorithm",
            "view_angle",
            "prediction_target",
            "feature_schema_version",
            "is_active",
            "created_at",
            "artifact_available",
            "training",
            "training_manifest",
            "features",
            "evaluation",
            "feature_warnings",
        ]
        read_only_fields = fields

    @staticmethod
    def _metric(metrics, key):
        value = metrics.get(key)

        return float(value) if isinstance(value, (int, float)) else None

    def get_artifact_available(self, obj):
        return bool(obj.artifact or obj.training_job.model_artifact)

    def get_training(self, obj):
        job = obj.training_job

        return {
            "job_id": job.id,
            "status": job.status,
            "view_angle": job.view_angle,
            "prediction_target": job.prediction_target,
            "feature_schema_version": job.feature_schema_version,
            "test_size": job.test_size,
            "dataset_names": [dataset.name for dataset in job.datasets.all()],
            "sample_count": job.sample_count,
            "train_count": job.train_count,
            "test_count": job.test_count,
            "split_strategy": job.split_strategy,
            "random_seed": job.random_seed,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
        }

    def get_training_manifest(self, obj):
        job = obj.training_job
        manifest = job.training_manifest or {}

        return manifest if isinstance(manifest, dict) else {}

    def get_features(self, obj):
        metrics = obj.training_job.metrics or obj.metrics or {}

        selected = (
            obj.training_job.feature_selection or metrics.get("feature_names") or []
        )

        importances = metrics.get("feature_importances") or {}

        return {
            "selected": list(selected),
            "importances": {
                str(name): float(value)
                for name, value in importances.items()
                if isinstance(value, (int, float))
            },
        }

    def get_evaluation(self, obj):
        metrics = obj.training_job.metrics or obj.metrics or {}

        confusion_matrix = metrics.get("confusion_matrix") or [[], []]

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
                metrics.get("overall_class_distribution") or {}
            ),
            "train_class_distribution": (metrics.get("train_class_distribution") or {}),
            "test_class_distribution": (metrics.get("test_class_distribution") or {}),
        }

    def get_feature_warnings(self, obj):
        return list(obj.training_job.feature_warnings or [])
