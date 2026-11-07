"""Shared role checks for authenticated account users."""


def is_annotator(user):
    """Return whether ``user`` has an annotator profile role.

    Staff access is intentionally separate: callers that allow administrators
    to perform annotator actions should check ``user.is_staff`` explicitly.
    """
    if not user or not getattr(user, "is_authenticated", False):
        return False

    profile = getattr(user, "profile", None)
    return bool(profile and profile.is_annotator)
