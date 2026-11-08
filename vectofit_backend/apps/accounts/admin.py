from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_annotator", "account_active", "account_staff")
    list_filter = ("is_annotator", "user__is_active", "user__is_staff")
    search_fields = ("user__username", "user__email")
    list_select_related = ("user",)
    autocomplete_fields = ("user",)

    @admin.display(boolean=True, ordering="user__is_active", description="Active account")
    def account_active(self, obj):
        return obj.user.is_active

    @admin.display(boolean=True, ordering="user__is_staff", description="Staff account")
    def account_staff(self, obj):
        return obj.user.is_staff
