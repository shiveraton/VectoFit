from django.contrib import admin
from .models import Dataset, DatasetSample


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "exercise_type", "purpose", "primary_target", "status", "created_at")
    list_filter = ("exercise_type", "purpose", "status", "created_at")
    search_fields = ("name", "description")
    ordering = ("-created_at",)

    def has_delete_permission(self, request, obj=None):
        return True

    actions = ['delete_selected']


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