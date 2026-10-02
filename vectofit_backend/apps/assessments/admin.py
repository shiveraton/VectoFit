from django.contrib import admin

from .models import AssessmentSession, RepAssessment, BodyProfile

class RepAssessmentInline(admin.TabularInline):
    model = RepAssessment
    extra = 0
    fields = (
        "rep_number",
        "jaa_score",
        "rom_score",
        "bad_score",
        "kvt_score",
        "hybrid_score",
        "classification",
    )
    readonly_fields = fields
    can_delete = False

@admin.register(BodyProfile)
class BodyProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "height_cm", "scale_factor", "calibrated_at")
    list_filter = ("calibrated_at",)
    search_fields = ("user__username",)

@admin.register(AssessmentSession)
class AssessmentSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "exercise_variant",
        "status",
        "created_at",
        "processed_at"
    )
    list_filter = ("exercise_variant", "status")
    search_fields = ("user__username",)
    inlines = [RepAssessmentInline]

@admin.register(RepAssessment)
class RepAssessment(admin.ModelAdmin):
    list_display = (
        "session",
        "rep_number",
        "jaa_score",
        "rom_score",
        "bad_score",
        "kvt_score",
        "hybrid_score",
        "classification",
    )
    list_filter = ("classification",)