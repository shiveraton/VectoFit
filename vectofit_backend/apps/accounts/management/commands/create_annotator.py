from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.roles import ANNOTATOR_GROUP


class Command(BaseCommand):
    help = "Create a non-staff annotation account."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--promote-existing", action="store_true")

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        user = User.objects.filter(username=username).first()
        group, _ = Group.objects.get_or_create(name=ANNOTATOR_GROUP)
        if user:
            if not options["promote_existing"]:
                self.stdout.write(f"User {username} exists; no changes made.")
                return
            if user.is_staff:
                raise CommandError("Refusing to add a staff account as an annotator.")
            user.groups.add(group)
            self.stdout.write(f"Added {username} to Annotators.")
            return
        password = getpass("Password: ")
        if not password:
            raise CommandError("Password cannot be empty.")
        user = User.objects.create_user(
            username=username, email=options["email"], password=password, is_staff=False
        )
        user.groups.add(group)
        self.stdout.write(f"Created annotator {username}.")
