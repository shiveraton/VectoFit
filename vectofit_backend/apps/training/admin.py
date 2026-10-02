"""Admin registrations so experiment runs are easy to inspect.

Supplementary infrastructure: the point is to let a researcher answer "what
did I run, on what, and what did it score?" without opening a shell.
"""

from django.contrib import admin

from .models import ModelRegistry, TrainingJob


@admin.register(TrainingJob)
class TrainingJobAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "algorithm",
        "status",
        "sample_count",
        "train_count",
        "test_count",
        "accuracy",
        "created_at",
    ]
    list_filter = ["status", "algorithm", "split_strategy", "created_at"]
    search_fields = ["id", "error_message"]
    readonly_fields = [
        "created_at",
        "started_at",
        "completed_at",
        "accuracy",
        "feature_warnings",
    ]
    filter_horizontal = ["datasets"]
    date_hierarchy = "created_at"

    @admin.display(description="test accuracy")
    def accuracy(self, obj):
        if not obj.metrics:
            return "-"
        value = obj.metrics.get("accuracy")
        return f"{value:.4f}" if value is not None else "-"


@admin.register(ModelRegistry)
class ModelRegistryAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "version",
        "algorithm",
        "training_job",
        "is_active",
        "created_at",
    ]
    list_filter = ["algorithm", "is_active", "created_at"]
    search_fields = ["name", "version", "training_job__id"]
    readonly_fields = ["created_at"]
