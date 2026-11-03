from typing import ClassVar

from django.contrib import admin

from .models import (
    AnnotationEvent,
    Dataset,
    DatasetAnnotatorAssignment,
    DatasetSample,
    Participant,
    ViewAngle,
)


@admin.register(AnnotationEvent)
class AnnotationEventAdmin(admin.ModelAdmin):
    list_display = ("id", "sample", "annotator", "entered_by", "action", "target_label", "created_at")
    list_filter = ("action", "annotator", "sample__dataset")
    search_fields = ("sample__id", "annotator__username", "entered_by__username", "target_label")
    readonly_fields = tuple(field.name for field in AnnotationEvent._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "participant_code",
        "created_at",
    )
    search_fields = ("participant_code",)


@admin.register(ViewAngle)
class ViewAngleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "angle_variant",
    )
    list_filter = ("angle_variant",)
    search_fields = ("angle_variant",)


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "exercise_type",
        "purpose",
        "primary_target",
        "status",
        "created_at",
    )
    list_filter = ("exercise_type", "purpose", "status", "created_at")
    search_fields = ("name", "description")
    ordering = ("-created_at",)

    def has_delete_permission(self, request, obj=None):
        return True

    actions: ClassVar[list] = ["delete_selected"]


@admin.register(DatasetAnnotatorAssignment)
class DatasetAnnotatorAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "dataset",
        "annotator",
        "is_active",
        "assigned_by",
        "assigned_at",
    )
    list_filter = ("is_active", "dataset")
    search_fields = ("dataset__name", "annotator__username", "annotator__email")
    autocomplete_fields = ("dataset",)
    raw_id_fields = ("annotator", "assigned_by")


@admin.register(DatasetSample)
class DatasetSampleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "dataset",
        "rep_assessment",
        "is_correct",
        "error_label",
        "annotator",
        "created_at",
    )
    list_filter = ("is_correct", "error_label", "dataset")
    search_fields = ("error_label", "dataset__name")
    raw_id_fields = ("dataset", "rep_assessment", "annotator")
    autocomplete_fields = ("dataset",)
