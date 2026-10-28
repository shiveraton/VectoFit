from django.contrib import admin

from .models import ExerciseVariant


@admin.register(ExerciseVariant)
class ExerciseVariantAdmin(admin.ModelAdmin):
    list_display = ("name", "variant_type", "created_at")
    list_filter = ("is_active", "variant_type")
    search_fields = ("name",)
