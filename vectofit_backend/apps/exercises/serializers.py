from rest_framework import serializers

from .models import ExerciseVariant

class ExerciseVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExerciseVariant
        fields = [
            "id",
            "name",
            "variant_type",
            "description",
            "is_active",
            "created_at",
        ]