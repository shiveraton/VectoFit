from typing import ClassVar

from rest_framework import serializers

from .models import InferenceRun, InferenceSimulation, ModelRegistry
from .services.inference_simulation import MAX_VIDEO_BYTES, validate_simulation_model


class InferenceRunRequestSerializer(serializers.Serializer):
    model_id = serializers.PrimaryKeyRelatedField(
        queryset=ModelRegistry.objects.select_related("training_job"),
    )

    def validate_model_id(self, model):
        try:
            validate_simulation_model(model)
        except (ValueError, OSError) as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return model


class InferenceUploadSerializer(InferenceRunRequestSerializer):
    video_file = serializers.FileField()

    def validate_video_file(self, video):
        if video.size > MAX_VIDEO_BYTES:
            raise serializers.ValidationError("Videos must be 200 MB or smaller.")
        return video


class InferenceRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = InferenceRun
        fields: ClassVar[list] = [
            "id",
            "model",
            "model_snapshot",
            "status",
            "error_message",
            "predictions",
            "model_loading_ms",
            "inference_ms",
            "created_at",
            "completed_at",
        ]


class InferenceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InferenceSimulation
        fields: ClassVar[list] = [
            "id",
            "original_filename",
            "status",
            "error_message",
            "created_at",
        ]


class InferenceSimulationSerializer(InferenceHistorySerializer):
    runs = InferenceRunSerializer(many=True, read_only=True)

    class Meta(InferenceHistorySerializer.Meta):
        fields: ClassVar[list] = [
            *InferenceHistorySerializer.Meta.fields,
            "feature_schema_version",
            "repetitions",
            "preprocessing_ms",
            "completed_at",
            "runs",
        ]
