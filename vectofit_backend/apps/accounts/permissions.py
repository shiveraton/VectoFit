from rest_framework.permissions import IsAdminUser

from .roles import is_validator


class IsAccountAdministrator(IsAdminUser):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and not is_validator(request.user)
