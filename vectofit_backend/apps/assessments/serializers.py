from rest_framework import serializers

from .models import AssessmentSession, BodyProfile, RepAssessment

class BodyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BodyProfile
        fields = [
            "id",
            "height_cm",
            "torso_length_cm",
            "femur_length-cm",
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
            "start_frame",
            "end_frame",
        ]

class AssessmentSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentSession
        fields = [
            "id",
            "exercise_variant",
            "body_profile",
            "video_file",
            "status",
            "created_at",
            "processed_at",
        ]
        read_only_fields = ["id", "status", "created_at", "processed_at"]

class AssessmentSessionDetailSerializer(AssessmentSessionSerializer):
    reps = RepAssessmentSerializer(many=True, read_only=True)

    class Meta(AssessmentSessionSerializer.Meta):
        fields = AssessmentSessionSerializer.Meta.fields + ["reps", "error_message"]