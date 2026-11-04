from rest_framework.permissions import BasePermission

from apps.accounts.models import Profile


class IsAnnotator(BasePermission):
    message = "An annotator account is required."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        is_annotator = Profile.objects.filter(
            user=request.user,
            is_annotator=True,
        ).exists()
        return request.user.is_staff or is_annotator
