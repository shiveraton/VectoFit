from typing import ClassVar

import cv2
from rest_framework import serializers

from .models import AssessmentSession, BodyProfile, RepAssessment
from .services.snapshot_overlay import reference_landmarks


class LandmarkInputSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    x_coordinate = serializers.FloatField()
    y_coordinate = serializers.FloatField()
    z_coordinate = serializers.FloatField(default=0.0)
    visibility = serializers.FloatField(default=0.0)


class BodyProfileDataInputSerializer(serializers.Serializer):
    height = serializers.FloatField(required=False, default=170.0)
    height_cm = serializers.FloatField(required=False, default=170.0)
    age = serializers.IntegerField(required=False)
    weight = serializers.FloatField(required=False)


class MorphologicalCalibrationRequestSerializer(serializers.Serializer):
    body_profile_data = BodyProfileDataInputSerializer(required=False)
    landmarks = LandmarkInputSerializer(many=True)


class BodyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BodyProfile
        fields: ClassVar[list] = [
            "id",
            "height_cm",
            "torso_length_cm",
            "femur_length_cm",
            "tibia_length_cm",
            "scale_factor",
            "raw_calibration_data",
            "calibrated_at",
        ]
        read_only_fields: ClassVar[list] = ["id", "calibrated_at"]


class RepAssessmentSerializer(serializers.ModelSerializer):
    snapshot_landmarks = serializers.SerializerMethodField()
    snapshot_frame_width = serializers.SerializerMethodField()
    snapshot_frame_height = serializers.SerializerMethodField()
    snapshot_reference_available = serializers.SerializerMethodField()

    def get_snapshot_landmarks(self, obj):
        series = obj.landmark_series or []
        if not series:
            return None
        if obj.key_frame_index is not None and obj.start_frame is not None:
            offset = obj.key_frame_index - obj.start_frame
            if 0 <= offset < len(series):
                return series[offset]
        return series[len(series) // 2]

    def _snapshot_size(self, obj):
        cache = self.context.setdefault("_snapshot_size_cache", {})
        session_id = obj.session_id
        if session_id in cache:
            return cache[session_id]
        try:
            capture = cv2.VideoCapture(obj.session.video_file.path)
            width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
            height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
            capture.release()
        except Exception:
            width, height = 0, 0
        cache[session_id] = (width, height)
        return cache[session_id]

    def get_snapshot_frame_width(self, obj):
        return self._snapshot_size(obj)[0] or None

    def get_snapshot_frame_height(self, obj):
        return self._snapshot_size(obj)[1] or None

    def get_snapshot_reference_available(self, obj):
        return reference_landmarks(obj) is not None

    class Meta:
        model = RepAssessment
        fields: ClassVar[list] = [
            "id",
            "rep_number",
            "jaa_score",
            "rom_score",
            "bad_score",
            "kvt_score",
            "hybrid_score",
            "classification",
            "analysis_result",
            "start_frame",
            "end_frame",
            "key_frame_index",
            "snapshot_landmarks",
            "snapshot_frame_width",
            "snapshot_frame_height",
            "snapshot_reference_available",
        ]
        read_only_fields: ClassVar[list] = ["analysis_result"]


class AssessmentSessionSerializer(serializers.ModelSerializer):
    rep_count = serializers.SerializerMethodField()
    exercise_variant_name = serializers.CharField(
        source="exercise_variant.name", read_only=True
    )

    def get_rep_count(self, obj):
        annotated_count = getattr(obj, "rep_count", None)
        return annotated_count if annotated_count is not None else obj.reps.count()

    class Meta:
        model = AssessmentSession
        fields: ClassVar[list] = [
            "id",
            "exercise_variant",
            "exercise_variant_name",
            "body_profile",
            "view_angle",
            "video_file",
            "status",
            "created_at",
            "processed_at",
            "rep_count",
            "error_message",
            "report",
        ]
        read_only_fields: ClassVar[list] = [
            "id",
            "status",
            "created_at",
            "processed_at",
            "error_message",
            "report",
        ]


class AssessmentSessionDetailSerializer(AssessmentSessionSerializer):
    reps = RepAssessmentSerializer(many=True, read_only=True, required=False)

    class Meta(AssessmentSessionSerializer.Meta):
        fields = AssessmentSessionSerializer.Meta.fields + ["reps"]

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")

        if request is None or request.query_params.get("include") != "reps":
            fields.pop("reps", None)

        return fields
