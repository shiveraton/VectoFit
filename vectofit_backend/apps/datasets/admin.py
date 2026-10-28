from typing import ClassVar

from django.contrib import admin

from .models import Dataset, DatasetSample, Participant, ViewAngle


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
