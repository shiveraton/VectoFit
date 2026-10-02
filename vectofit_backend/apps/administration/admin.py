from django.contrib import admin
from .models import MLModel, TrainingJob, EvaluationResult

@admin.register(MLModel)
class MLModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'version', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'version')
    ordering = ('-created_at',)

@admin.register(TrainingJob)
class TrainingJobAdmin(admin.ModelAdmin):
    list_display = ('model', 'status', 'started_at')
    list_filter = ('status', 'started_at')
    readonly_fields = ('started_at', 'completed_at', 'logs', 'error_message')

@admin.register(EvaluationResult)
class EvaluationResultAdmin(admin.ModelAdmin):
    list_display = ('model', 'test_dataset_version', 'accuracy', 'f1_score', 'evaluated_at')
    readonly_fields = ('evaluated_at',)