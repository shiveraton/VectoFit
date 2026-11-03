from django.contrib.auth.models import Group

ANNOTATOR_GROUP = "Annotators"


def is_annotator(user):
    return bool(
        user
        and user.is_authenticated
        and user.groups.filter(name=ANNOTATOR_GROUP).exists()
    )


def annotator_group():
    group, _ = Group.objects.get_or_create(name=ANNOTATOR_GROUP)
    return group


def grant_annotator(user):
    """Add ``user`` to the Annotators group unless they are staff.

    Returns True when the membership did not already exist.
    """
    if user is None:
        return False
    if user.is_staff:
        return False
    group = annotator_group()
    if user.groups.filter(pk=group.pk).exists():
        return False
    user.groups.add(group)
    return True


def revoke_annotator(user):
    if user is None:
        return False
    group = Group.objects.filter(name=ANNOTATOR_GROUP).first()
    if group is None:
        return False
    removed = user.groups.filter(pk=group.pk).exists()
    if removed:
        user.groups.remove(group)
    return removed
