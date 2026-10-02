from rest_framework import serializers
from .models import MLModel, TrainingJob, EvaluationResult

class MLModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MLModel
        fields = '__all__'

class TrainingJobSerializer(serializers.ModelSerializer):
    model_name = serializers.CharField(source='model.name', read_only=True)
    model_version = serializers.CharField(source='model.version', read_only=True)

    class Meta:
        model = TrainingJob
        fields = '__all__'

class EvaluationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationResult
        fields = '__all__'
