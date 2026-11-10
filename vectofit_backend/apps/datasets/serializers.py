from django.db.models import Q
from rest_framework import serializers

upload_token = serializers.UUIDField(
    source="upload_token", help_text="Token returned by the archive preview endpoint."
)

from typing import ClassVar

from apps.assessments.serializers import RepAssessmentSerializer
from .media_views import signed_dataset_media_url

from .models import (
    Dataset,
    DatasetSample,
    DatasetVideo,
    KneeAnnotation,
    Participant,
    ViewAngle,
)
from .services.annotation import latest_annotation
from .services.knee_label import final_knee_target, knee_target
from .services.frontal import require_frontal_annotation, sample_angle


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
            if not isinstance(item["grade"], str) or item["grade"] not in allowed_grades:
                raise serializers.ValidationError(f"Invalid {side} knee grade.")
            if (
                item["direction"] is not None
                and (not isinstance(item["direction"], str) or item["direction"] not in allowed_directions)
            ):
                raise serializers.ValidationError(f"Invalid {side} knee direction.")
        if not isinstance(value["symmetry_observation"], str) or value["symmetry_observation"] not in {
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
    def validate(self, attrs):
        if "knee_annotation" in attrs and self.instance is not None:
            require_frontal_annotation(self.instance)
            from .services.assignments import review_samples

            if not review_samples().filter(pk=self.instance.pk).exists():
                raise serializers.ValidationError("This sample is not available for annotation.")
        return super().validate(attrs)

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
    view_angle_name = serializers.SerializerMethodField()
    video_fps = serializers.SerializerMethodField()
    is_manually_annotated = serializers.SerializerMethodField()

    rep_assessment = RepAssessmentSerializer(read_only=True)

    class Meta:
        model = DatasetSample
        fields: ClassVar[list] = [
            "id",
            "dataset",
            "dataset_video",
            "view_angle_name",
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

    def get_view_angle_name(self, obj):
        return sample_angle(obj)

    def get_dataset_video(self, obj):
        if obj.dataset_video_id is None:
            return None

        video = obj.dataset_video
        request = self.context.get("request")
        video_url = (
            signed_dataset_media_url(request, "dataset-video", video.pk, video.dataset)
            if video.video_file
            else None
        )
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
        target = knee_target(annotation)
        return None if target == "incomplete" else target

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
        return signed_dataset_media_url(request, "dataset", obj.pk, obj)

    def get_sample_count(self, obj):
        if hasattr(obj, "summary_samples"):
            return len(obj.summary_samples)
        return obj.samples.count()

    def get_labelled_sample_count(self, obj):
        if hasattr(obj, "summary_samples"):
            return sum(sample.is_correct is not None for sample in obj.summary_samples)
        return obj.samples.filter(is_correct__isnull=False).count()

    def get_is_usable_for_training(self, obj):
        return self.get_labelled_sample_count(obj) > 0

    def get_video_count(self, obj):
        if hasattr(obj, "summary_videos"):
            return len(obj.summary_videos)
        return obj.videos.count()

    def get_ready_video_count(self, obj):
        if hasattr(obj, "summary_videos"):
            return sum(video.status == DatasetVideo.Status.READY for video in obj.summary_videos)
        return obj.videos.filter(status="READY").count()

    def get_failed_video_count(self, obj):
        if hasattr(obj, "summary_videos"):
            return sum(video.status == DatasetVideo.Status.FAILED for video in obj.summary_videos)
        return obj.videos.filter(status="FAILED").count()

    def get_inherited_labelled_sample_count(self, obj):
        if hasattr(obj, "summary_samples"):
            return sum(
                sample.is_correct is not None and sample.annotator_id is None
                and sample.annotated_at is None for sample in obj.summary_samples
            )
        return obj.samples.filter(
            is_correct__isnull=False,
            annotator__isnull=True,
            annotated_at__isnull=True,
        ).count()

    def _review_progress(self, obj):
        from .services.assignments import review_samples
        from .services.knee_label import knee_label_evidence

        cache = getattr(self, "_review_progress_cache", None)
        if cache is None:
            cache = self._review_progress_cache = {}
        if obj.pk not in cache:
            samples = list(review_samples().filter(dataset=obj).prefetch_related("knee_annotation_records"))
            reviewed = sum(
                any(record["annotator_id"] is not None and record["annotation"] is not None
                    for record in knee_label_evidence(sample)["annotations"])
                for sample in samples
            )
            cache[obj.pk] = (len(samples), reviewed)
        return cache[obj.pk]

    def get_review_selected_sample_count(self, obj):
        return self._review_progress(obj)[0]

    def get_human_reviewed_sample_count(self, obj):
        return self._review_progress(obj)[1]

    def get_pending_review_sample_count(self, obj):
        total, reviewed = self._review_progress(obj)
        return total - reviewed

    def get_participant_count(self, obj):
        if hasattr(obj, "summary_videos"):
            return len({video.participant_id for video in obj.summary_videos if video.participant_id})
        return (
            obj.videos.filter(participant__isnull=False)
            .values("participant_id")
            .distinct()
            .count()
        )

    def get_view_angles(self, obj):
        if hasattr(obj, "summary_videos"):
            angles = sorted({
                video.view_angle.angle_variant for video in obj.summary_videos
                if video.view_angle_id is not None
            })
            if not angles and obj.view_angle_id and obj.view_angle:
                angles = [obj.view_angle.angle_variant]
            return angles
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
        if hasattr(obj, "summary_samples") and hasattr(obj, "summary_videos"):
            return self._get_prefetched_angle_training_stats(obj)
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

            knee_counts = {
                "good": 0,
                "bad": 0,
                "borderline": 0,
                "unassessable": 0,
                "disputed": 0,
                "missing": 0,
            }
            for sample in samples:
                target = final_knee_target(sample)
                knee_counts[target if target in knee_counts else "missing"] += 1

            stats[angle] = {
                "sample_count": samples.count(),
                "labelled_sample_count": labelled.count(),
                "good_count": labelled.filter(is_correct=True).count(),
                "bad_count": incorrect.count(),
                "error_type_sample_count": labelled.filter(is_correct=True).count()
                + sum(error_labels.values()),
                "error_label_counts": error_labels,
                "knee_target_sample_count": knee_counts["good"] + knee_counts["bad"],
                "knee_label_counts": knee_counts,
                "participant_count": participant_count,
                "video_count": videos.count(),
            }
        return stats

    def _get_prefetched_angle_training_stats(self, obj):
        stats = {}
        videos = obj.summary_videos
        samples = obj.summary_samples
        has_videos = bool(videos)
        for angle in self.get_view_angles(obj):
            if has_videos:
                angle_videos = [
                    video for video in videos
                    if video.status == DatasetVideo.Status.READY
                    and video.view_angle_id is not None
                    and video.view_angle.angle_variant == angle
                ]
                angle_samples = [
                    sample for sample in samples
                    if sample.dataset_video_id is not None
                    and sample.dataset_video.status == DatasetVideo.Status.READY
                    and sample.dataset_video.view_angle.angle_variant == angle
                ]
                participant_count = len({
                    video.participant_id for video in angle_videos if video.participant_id
                })
            else:
                angle_videos = []
                angle_samples = [sample for sample in samples if sample.dataset_video_id is None]
                participant_count = 1 if obj.participant_id else 0

            labelled = [sample for sample in angle_samples if sample.is_correct is not None]
            incorrect = [sample for sample in labelled if sample.is_correct is False]
            error_labels = {}
            for sample in incorrect:
                label = "_".join((sample.error_label or "").strip().casefold().split())
                if label and label != "correct_form":
                    error_labels[label] = error_labels.get(label, 0) + 1
            knee_counts = {
                "good": 0, "bad": 0, "borderline": 0,
                "unassessable": 0, "disputed": 0, "missing": 0,
            }
            for sample in angle_samples:
                target = final_knee_target(sample)
                knee_counts[target if target in knee_counts else "missing"] += 1
            stats[angle] = {
                "sample_count": len(angle_samples),
                "labelled_sample_count": len(labelled),
                "good_count": sum(sample.is_correct is True for sample in labelled),
                "bad_count": len(incorrect),
                "error_type_sample_count": sum(sample.is_correct is True for sample in labelled)
                + sum(error_labels.values()),
                "error_label_counts": error_labels,
                "knee_target_sample_count": knee_counts["good"] + knee_counts["bad"],
                "knee_label_counts": knee_counts,
                "participant_count": participant_count,
                "video_count": len(angle_videos),
            }
        return stats


class DatasetListSerializer(DatasetSerializer):
    """Dataset summaries without the full sample payload unused by the table."""

    class Meta(DatasetSerializer.Meta):
        fields = [field for field in DatasetSerializer.Meta.fields if field != "samples"]


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
