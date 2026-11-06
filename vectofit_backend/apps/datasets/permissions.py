from rest_framework.permissions import BasePermission

from apps.accounts.roles import is_annotator


class IsAnnotator(BasePermission):
    message = "An annotator account is required."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_staff or is_annotator(request.user)
