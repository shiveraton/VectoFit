from typing import ClassVar

from django.contrib import admin

from .models import (
    Dataset,
    DatasetAnnotatorAssignment,
    DatasetSample,
    Participant,
    ViewAngle,
)


@admin.register(DatasetAnnotatorAssignment)
class DatasetAnnotatorAssignmentAdmin(admin.ModelAdmin):
    list_display = ("dataset", "annotator", "is_active", "assigned_at")
    list_filter = ("is_active", "dataset")
    search_fields = ("dataset__name", "annotator__username")
    autocomplete_fields = ("dataset", "annotator")
    readonly_fields = ("assigned_at",)
    list_select_related = ("dataset", "annotator")

    def get_readonly_fields(self, request, obj=None):
        return ("assigned_at", "dataset", "annotator") if obj else ("assigned_at",)

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        from .services.assignments import set_assignment

        saved = set_assignment(obj.dataset, obj.annotator, obj.is_active, request.user)
        if saved is None:
            super().save_model(request, obj, form, change)
        else:
            obj.pk = saved.pk
            obj.assigned_at = saved.assigned_at
            obj._state.adding = False
            obj._state.db = saved._state.db

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "annotator":
            from django.contrib.auth import get_user_model

            kwargs["queryset"] = get_user_model().objects.filter(
                is_active=True,
                is_staff=False,
                is_superuser=False,
                profile__is_annotator=True,
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


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
