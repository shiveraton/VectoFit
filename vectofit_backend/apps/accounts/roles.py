def is_annotator(user):
    if not user or not getattr(user, "is_authenticated", False):
        return False

    profile = getattr(user, "profile", None)
    return bool(profile and profile.is_annotator and not profile.is_validator)


def is_validator(user):
    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    return bool(getattr(getattr(user, "profile", None), "is_validator", False))
