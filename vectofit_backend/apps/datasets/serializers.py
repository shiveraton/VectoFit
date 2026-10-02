from rest_framework import serializers

from .models import Dataset, DatasetSample

class DatasetSampleSerializer(serializers.ModelSerializer):
    is_correct = serializers.BooleanField(
        allow_null=True,
        required=False,
        help_text="Coarse ground-truth label. Null means unlabelled and is "
                  "excluded from training.",
    )

    class Meta:
        model = DatasetSample
        fields = [
            "id",
            "dataset",
            "rep_assessment",
            "is_correct",
            "error_label",
            "annotator",
            "annotated_at",
            "created_at",
        ]
        read_only_fields = ["annotator", "annotated_at", "created_at"]

class DatasetSerializer(serializers.ModelSerializer):
    samples = DatasetSampleSerializer(many=True, read_only=True)
    video_file = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    sample_count = serializers.SerializerMethodField()
    labelled_sample_count = serializers.SerializerMethodField()
    is_usable_for_training = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = [
            "id",
            "name",
            "description",
            "exercise_type",
            "purpose",
            "primary_target",
            "secondary_target",
            "created_at",
            "updated_at",
            "samples",
            "sample_count",
            "labelled_sample_count",
            "is_usable_for_training",
            "status",
            "error_message",
            "video_file",
            "video_url",
        ]
        read_only_fields = ["error_message", "created_at", "updated_at"]

    def get_video_file(self, obj):
        if obj.video_file:
            return self.context['request'].build_absolute_uri(obj.video_file.url)
        return None

    def get_video_url(self, obj):
        return obj.video_file.url if obj.video_file else None

    def get_sample_count(self, obj):
        return obj.samples.count()

    def get_labelled_sample_count(self, obj):
        return obj.samples.filter(is_correct__isnull=False).count()

    def get_is_usable_for_training(self, obj):
        return self.get_labelled_sample_count(obj) > 0