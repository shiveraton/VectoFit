from rest_framework import serializers

from .models import ValidationAnnotation


class ValidationAnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValidationAnnotation
        fields = ["id", "repetition", "left_knee", "right_knee", "overall", "notes",
                  "protocol_version", "created_at"]
        read_only_fields = ["id", "repetition", "overall", "protocol_version", "created_at"]

    def to_internal_value(self, data):
        unexpected = set(data) - {"left_knee", "right_knee", "notes"}
        if unexpected:
            raise serializers.ValidationError({key: "This field cannot be set." for key in unexpected})
        return super().to_internal_value(data)
