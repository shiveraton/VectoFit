
from rest_framework import serializers

from .models import AssessmentSession, BodyProfile, RepAssessment

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
        fields = [
            "id",
            "height_cm",
            "torso_length_cm",
            "femur_length_cm",
            "tibia_length_cm",
            "scale_factor",
            "raw_calibration_data",
            "calibrated_at",
        ]
        read_only_fields = ["id", "calibrated_at"]

class RepAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepAssessment
        fields = [
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
        ]
        read_only_fields = ["analysis_result"]

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
        fields = [
            "id",
            "exercise_variant",
            "exercise_variant_name",
            "body_profile",
            "video_file",
            "status",
            "created_at",
            "processed_at",
            "rep_count",
            "error_message"
        ]
        read_only_fields = ["id", "status", "created_at", "processed_at", "error_message"]

class AssessmentSessionDetailSerializer(AssessmentSessionSerializer):
    reps = RepAssessmentSerializer(many=True, read_only=True)

    class Meta(AssessmentSessionSerializer.Meta):
        fields = AssessmentSessionSerializer.Meta.fields + ["reps"]
