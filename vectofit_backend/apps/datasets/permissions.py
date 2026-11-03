from rest_framework.permissions import BasePermission

from apps.accounts.roles import is_annotator


class IsAnnotatorOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and (user.is_staff or is_annotator(user))
        )
