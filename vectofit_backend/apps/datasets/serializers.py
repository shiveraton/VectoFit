from rest_framework import serializers
from apps.assessments.serializers import RepAssessmentSerializer
from .models import Dataset, DatasetVideo, DatasetSample, Participant, ViewAngle

class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participant
        fields = [
            "id",
            "participant_code",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "participant_code",
            "created_at",
        ]

    def create(self, validated_data):
        last_participant = (
            Participant.objects
            .order_by("-id")
            .first()
        )

        next_number = last_participant.id + 1 if last_participant else 1
        participant_code = f"P{next_number:03d}"

        return Participant.objects.create(
            participant_code=participant_code
        )

class ViewAngleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViewAngle
        fields = [
            "id",
            "angle_variant",
        ]
        read_only_fields = [
            "id",
            "angle_variant",
        ]

class DatasetSampleSerializer(serializers.ModelSerializer):
    is_correct = serializers.BooleanField(
        allow_null=True,
        required=False,
        help_text=(
            "Coarse ground-truth label. Null means unlabelled "
            "and is excluded from training."
        ),
    )

    dataset_video = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    rep_assessment = RepAssessmentSerializer(read_only=True)

    class Meta:
        model = DatasetSample
        fields = [
            "id",
            "dataset",
            "dataset_video",
            "rep_assessment",
            "is_correct",
            "error_label",
            "annotator",
            "annotated_at",
            "created_at",
        ]
        read_only_fields = [
            "dataset",
            "rep_assessment",
            "annotator",
            "annotated_at",
            "created_at",
        ]

class DatasetSerializer(serializers.ModelSerializer):
    samples = DatasetSampleSerializer(many=True, read_only=True)
    view_angle = serializers.PrimaryKeyRelatedField(
        queryset=ViewAngle.objects.all(),
        allow_null=True,
        required=False,
    )
    video_file = serializers.FileField(
        required=False,
        allow_null=True
    )
    video_url = serializers.SerializerMethodField()
    sample_count = serializers.SerializerMethodField()
    labelled_sample_count = serializers.SerializerMethodField()
    is_usable_for_training = serializers.SerializerMethodField()
    video_count = serializers.SerializerMethodField()
    ready_video_count = serializers.SerializerMethodField()
    failed_video_count = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields = [
            "id",
            "name",
            "description",
            "participant",
            "view_angle",
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
            "video_count",
            "ready_video_count",
            "failed_video_count"
        ]
        read_only_fields = [
            "id",
            "status",
            "error_message",
            "created_at",
            "updated_at",
            "samples",
            "sample_count",
            "labelled_sample_count",
            "is_usable_for_training",
            "video_url",
            "video_count",
            "ready_video_count",
            "failed_video_count"
        ]

    def get_video_file(self, obj):
        if not obj.video_file:
            return None

        request = self.context.get("request")

        if request is not None:
            return request.build_absolute_uri(obj.video_file.url)

        return obj.video_file.url

    def get_video_url(self, obj):
        if not obj.video_file:
            return None

        request = self.context.get("request")

        if request is not None:
            return request.build_absolute_uri(obj.video_file.url)

        return obj.video_file.url

    def get_sample_count(self, obj):
        return obj.samples.count()

    def get_labelled_sample_count(self, obj):
        return obj.samples.filter(is_correct__isnull=False).count()

    def get_is_usable_for_training(self, obj):
        return self.get_labelled_sample_count(obj) > 0

    def get_video_count(self, obj):
        return obj.videos.count()

    def get_ready_video_count(self, obj):
        return obj.videos.filter(
            status="READY"
        ).count()

    def get_failed_video_count(self, obj):
        return obj.videos.filter(
            status="FAILED"
        ).count()

class DatasetVideoSerializer(serializers.ModelSerializer):
    participant_code = serializers.CharField(
        source="participant.participant_code",
        read_only=True,
    )

    view_angle_name = serializers.CharField(
        source="view_angle.angle_variant",
        read_only=True,
    )

    video_url = serializers.SerializerMethodField()

    class Meta:
        model = DatasetVideo
        fields = [
            "id",
            "dataset",
            "participant",
            "participant_code",
            "view_angle",
            "view_angle_name",
            "video_file",
            "video_url",
            "source_label",
            "source_path",
            "status",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_video_url(self, obj):
        if not obj.video_file:
            return None

        request = self.context.get("request")
        url = obj.video_file.url

        return (
            request.build_absolute_uri(url)
            if request
            else url
        )

class DatasetBulkImportSerializer(serializers.Serializer):
    token = serializers.UUIDField(
        help_text="Token returned by the archive preview endpoint."
    )

    name = serializers.CharField(
        max_length=50,
        trim_whitespace=True,
    )

    description = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )

    exercise_type = serializers.ChoiceField(
        choices=Dataset.EXERCISE_CHOICES,
    )

    purpose = serializers.ChoiceField(
        choices=Dataset.PURPOSE_CHOICES,
    )

    primary_target = serializers.CharField(
        max_length=50,
        required=False,
        default="biomechanical_errors",
    )

    secondary_target = serializers.CharField(
        max_length=50,
        required=False,
        default="biomechanical_errors",
    )

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Dataset name cannot be empty."
            )

        return value