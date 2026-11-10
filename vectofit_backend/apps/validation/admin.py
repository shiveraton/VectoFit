from django.contrib import admin
from .models import ValidationAnnotation, ValidationAnnotationEvent, ValidationSample


class ReadOnlyValidationAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ValidationAnnotation)
class ValidationAnnotationAdmin(ReadOnlyValidationAdmin):
    list_display = ["id", "repetition_id", "validator", "overall", "protocol_version", "created_at"]
    list_filter = ["protocol_version", "overall"]
    list_select_related = ["validator"]


@admin.register(ValidationAnnotationEvent)
class ValidationAnnotationEventAdmin(ReadOnlyValidationAdmin):
    list_display = ["id", "annotation_id", "source", "created_at"]


@admin.register(ValidationSample)
class ValidationSampleAdmin(ReadOnlyValidationAdmin):
    list_display = ["position", "repetition_id", "protocol_version", "created_at"]
