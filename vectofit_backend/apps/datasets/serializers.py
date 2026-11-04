from django.db.models import Q
from rest_framework import serializers

upload_token = serializers.UUIDField(
    source="upload_token", help_text="Token returned by the archive preview endpoint."
)

from typing import ClassVar

from apps.assessments.serializers import RepAssessmentSerializer

from .models import (
    Dataset,
    DatasetSample,
    DatasetVideo,
    KneeAnnotation,
    Participant,
    ViewAngle,
)
from .services.annotation import latest_annotation
from .services.knee_label import knee_target


class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participant
        fields: ClassVar[list] = [
            "id",
            "participant_code",
            "created_at",
        ]
        read_only_fields: ClassVar[list] = [
            "id",
            "participant_code",
            "created_at",
        ]

    def create(self, validated_data):
        last_participant = Participant.objects.order_by("-id").first()

        next_number = last_participant.id + 1 if last_participant else 1
        participant_code = f"P{next_number:03d}"

        return Participant.objects.create(participant_code=participant_code)


class ViewAngleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViewAngle
        fields: ClassVar[list] = [
            "id",
            "angle_variant",
        ]
        read_only_fields: ClassVar[list] = [
            "id",
            "angle_variant",
        ]


class KneeAnnotationField(serializers.Field):
    def get_attribute(self, instance):
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None
        return latest_annotation(instance, user)

    def to_representation(self, record):
        return record.annotation if record else None

    def to_internal_value(self, value):
        if value is None:
            return None
        if not isinstance(value, dict):
            raise serializers.ValidationError("Expected an annotation object or null.")
        required = {"left", "right", "symmetry_observation", "notes"}
        if set(value) != required:
            raise serializers.ValidationError(
                "Annotation fields are incomplete or unexpected."
            )
        allowed_grades = {"aligned", "borderline", "deviated", "unassessable"}
        allowed_directions = {"valgus", "varus", "none", "uncertain"}
        for side in ("left", "right"):
            item = value[side]
            if not isinstance(item, dict) or set(item) != {"grade", "direction"}:
                raise serializers.ValidationError(f"Invalid {side} knee annotation.")
            if item["grade"] is not None and item["grade"] not in allowed_grades:
                raise serializers.ValidationError(f"Invalid {side} knee grade.")
            if (
                item["direction"] is not None
                and item["direction"] not in allowed_directions
            ):
                raise serializers.ValidationError(f"Invalid {side} knee direction.")
        if value["symmetry_observation"] not in {
            "symmetric",
            "asymmetric",
            "uncertain",
            "not_recorded",
        }:
            raise serializers.ValidationError("Invalid symmetry observation.")
        if not isinstance(value["notes"], str):
            raise serializers.ValidationError("Notes must be text.")
        return value


class DatasetSampleSerializer(serializers.ModelSerializer):
    knee_annotation = KneeAnnotationField(required=False, allow_null=True)
    target_label = serializers.SerializerMethodField()
    is_correct = serializers.BooleanField(
        allow_null=True,
        required=False,
        help_text=(
            "Coarse ground-truth label. Null means unlabelled "
            "and is excluded from training."
        ),
    )

    dataset_video = serializers.SerializerMethodField()
    video_fps = serializers.SerializerMethodField()
    is_manually_annotated = serializers.SerializerMethodField()

    rep_assessment = RepAssessmentSerializer(read_only=True)

    class Meta:
        model = DatasetSample
        fields: ClassVar[list] = [
            "id",
            "dataset",
            "dataset_video",
            "video_fps",
            "is_manually_annotated",
            "knee_annotation",
            "target_label",
            "rep_assessment",
            "is_correct",
            "error_label",
            "annotator",
            "annotated_at",
            "created_at",
        ]
        read_only_fields: ClassVar[list] = [
            "dataset",
            "rep_assessment",
            "annotator",
            "annotated_at",
            "created_at",
        ]

    def get_dataset_video(self, obj):
        if obj.dataset_video_id is None:
            return None

        video = obj.dataset_video
        request = self.context.get("request")
        video_url = video.video_file.url if video.video_file else None
        if request is not None and video_url:
            video_url = request.build_absolute_uri(video_url)
        return {
            "id": video.pk,
            "video_url": video_url,
            "participant_code": video.participant.participant_code,
            "view_angle_name": video.view_angle.angle_variant,
            "source_label": video.source_label,
            "source_path": video.source_path,
            "requires_manual_review": video.requires_manual_review,
        }

    def get_knee_annotation(self, obj):
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None
        record = latest_annotation(obj, user)
        return record.annotation if record else None

    def get_target_label(self, obj):
        annotation = self.get_knee_annotation(obj)
        if not annotation:
            return None
        grades = [annotation.get(side, {}).get("grade") for side in ("left", "right")]
        if any(grade is None for grade in grades):
            return None
        return knee_target(annotation)

    def update(self, instance, validated_data):
        annotation = validated_data.pop("knee_annotation", serializers.empty)
        instance = super().update(instance, validated_data)
        if annotation is not serializers.empty:
            request = self.context.get("request")
            user = request.user if request else None
            KneeAnnotation.objects.create(
                sample=instance,
                annotation=annotation,
                annotator=user if user and user.is_authenticated else None,
            )
        return instance

    def get_video_fps(self, obj):
        return self.context.get("video_fps_by_id", {}).get(obj.dataset_video_id)

    def get_is_manually_annotated(self, obj):
        return obj.annotator_id is not None or obj.annotated_at is not None


class DatasetSerializer(serializers.ModelSerializer):
    samples = DatasetSampleSerializer(many=True, read_only=True)
    view_angle = serializers.PrimaryKeyRelatedField(
        queryset=ViewAngle.objects.all(),
        allow_null=True,
        required=False,
    )
    video_file = serializers.FileField(required=False, allow_null=True)
    video_url = serializers.SerializerMethodField()
    sample_count = serializers.SerializerMethodField()
    labelled_sample_count = serializers.SerializerMethodField()
    is_usable_for_training = serializers.SerializerMethodField()
    video_count = serializers.SerializerMethodField()
    ready_video_count = serializers.SerializerMethodField()
    failed_video_count = serializers.SerializerMethodField()
    inherited_labelled_sample_count = serializers.SerializerMethodField()
    review_selected_sample_count = serializers.SerializerMethodField()
    human_reviewed_sample_count = serializers.SerializerMethodField()
    pending_review_sample_count = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()
    view_angles = serializers.SerializerMethodField()
    angle_training_stats = serializers.SerializerMethodField()

    class Meta:
        model = Dataset
        fields: ClassVar[list] = [
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
            "failed_video_count",
            "review_policy",
            "selection_method",
            "review_count",
            "random_seed",
            "selected_video_paths",
            "inherited_labelled_sample_count",
            "review_selected_sample_count",
            "human_reviewed_sample_count",
            "pending_review_sample_count",
            "participant_count",
            "view_angles",
            "angle_training_stats",
        ]
        read_only_fields: ClassVar[list] = [
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
            "failed_video_count",
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
        return obj.videos.filter(status="READY").count()

    def get_failed_video_count(self, obj):
        return obj.videos.filter(status="FAILED").count()

    def get_inherited_labelled_sample_count(self, obj):
        return obj.samples.filter(
            is_correct__isnull=False,
            annotator__isnull=True,
            annotated_at__isnull=True,
        ).count()

    def get_review_selected_sample_count(self, obj):
        return obj.samples.filter(
            dataset_video__requires_manual_review=True,
        ).count()

    def get_human_reviewed_sample_count(self, obj):
        return (
            obj.samples.filter(
                dataset_video__requires_manual_review=True,
            )
            .filter(Q(annotator__isnull=False) | Q(annotated_at__isnull=False))
            .count()
        )

    def get_pending_review_sample_count(self, obj):
        return obj.samples.filter(
            dataset_video__requires_manual_review=True,
            annotator__isnull=True,
            annotated_at__isnull=True,
        ).count()

    def get_participant_count(self, obj):
        return (
            obj.videos.filter(participant__isnull=False)
            .values("participant_id")
            .distinct()
            .count()
        )

    def get_view_angles(self, obj):
        angles = list(
            obj.videos.filter(view_angle__isnull=False)
            .values_list("view_angle__angle_variant", flat=True)
            .distinct()
            .order_by("view_angle__angle_variant")
        )
        if not angles and obj.view_angle_id and obj.view_angle:
            angles = [obj.view_angle.angle_variant]
        return angles

    def get_angle_training_stats(self, obj):
        """Return the label counts the training configuration needs per view."""
        stats = {}
        has_videos = obj.videos.exists()

        for angle in self.get_view_angles(obj):
            if has_videos:
                samples = obj.samples.filter(
                    dataset_video__status=DatasetVideo.Status.READY,
                    dataset_video__view_angle__angle_variant=angle,
                )
                videos = obj.videos.filter(
                    status=DatasetVideo.Status.READY,
                    view_angle__angle_variant=angle,
                )
                participant_count = (
                    videos.exclude(participant__isnull=True)
                    .values("participant_id")
                    .distinct()
                    .count()
                )
            else:
                samples = obj.samples.filter(dataset_video__isnull=True)
                videos = obj.videos.none()
                participant_count = 1 if obj.participant_id else 0

            labelled = samples.filter(is_correct__isnull=False)
            incorrect = labelled.filter(is_correct=False)
            error_labels = {}
            for value in incorrect.values_list("error_label", flat=True):
                label = "_".join((value or "").strip().casefold().split())
                if label and label != "correct_form":
                    error_labels[label] = error_labels.get(label, 0) + 1

            stats[angle] = {
                "sample_count": samples.count(),
                "labelled_sample_count": labelled.count(),
                "good_count": labelled.filter(is_correct=True).count(),
                "bad_count": incorrect.count(),
                "error_type_sample_count": labelled.filter(is_correct=True).count()
                + sum(error_labels.values()),
                "error_label_counts": error_labels,
                "participant_count": participant_count,
                "video_count": videos.count(),
            }
        return stats


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
        fields: ClassVar[list] = [
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
            "requires_manual_review",
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

        return request.build_absolute_uri(url) if request else url


class DatasetBulkImportSerializer(serializers.Serializer):
    upload_token = serializers.UUIDField(
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
    review_policy = serializers.ChoiceField(
        choices=Dataset.ReviewPolicy.choices,
        required=False,
        default=Dataset.ReviewPolicy.SOURCE,
    )
    selection_method = serializers.ChoiceField(
        choices=Dataset.SelectionMethod.choices,
        required=False,
        default=Dataset.SelectionMethod.STRATIFIED,
    )
    review_count = serializers.IntegerField(
        required=False, min_value=0, allow_null=True
    )
    random_seed = serializers.IntegerField(required=False, min_value=0, allow_null=True)
    selected_video_paths = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False,
        default=list,
    )

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError("Dataset name cannot be empty.")

        return value

    def validate(self, attrs):
        paths = attrs.get("selected_video_paths", [])
        policy = attrs["review_policy"]
        review_count = attrs.get("review_count")

        if len(paths) != len(set(paths)):
            raise serializers.ValidationError(
                {"selected_video_paths": "Selected video paths must be unique."}
            )

        if policy == Dataset.ReviewPolicy.SUBSET and not paths:
            raise serializers.ValidationError(
                {"selected_video_paths": "Select at least one video for subset review."}
            )

        if (
            review_count is not None
            and policy == Dataset.ReviewPolicy.SUBSET
            and review_count != len(paths)
        ):
            raise serializers.ValidationError(
                {"review_count": "Review count must match the selected video paths."}
            )

        return attrs
