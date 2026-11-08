"""Preview or copy eligible annotator identities into the default database."""

import copy
import json
import os

import dj_database_url
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction

from apps.accounts.models import Profile


def transfer_accounts(source, destination, *, apply=False):
    User = get_user_model()
    users = list(
        User.objects.using(source)
        .filter(
            is_active=True,
            is_staff=False,
            is_superuser=False,
            profile__is_annotator=True,
        )
        .order_by("pk")
    )
    report = {"mode": "apply" if apply else "preview", "accounts": [], "conflicts": []}
    names, emails = set(), set()
    for user in users:
        reasons = []
        if (
            user.username.casefold() in names
            or User.objects.using(destination)
            .filter(username__iexact=user.username)
            .exists()
        ):
            reasons.append("username already exists (ignoring case)")
        email = user.email.strip().casefold()
        if email and (
            email in emails
            or User.objects.using(destination)
            .filter(email__iexact=user.email.strip())
            .exists()
        ):
            reasons.append("email already exists (ignoring case)")
        names.add(user.username.casefold())
        if email:
            emails.add(email)
        report["accounts"].append({"source_id": user.pk, "username": user.username})
        if reasons:
            report["conflicts"].append(
                {"source_id": user.pk, "username": user.username, "reasons": reasons}
            )
    report["created"] = 0
    if not apply or report["conflicts"]:
        return report
    for user, row in zip(users, report["accounts"]):
        created = User.objects.using(destination).create(
            username=user.username,
            email=user.email,
            password=user.password,
            first_name=user.first_name,
            last_name=user.last_name,
            date_joined=user.date_joined,
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        Profile.objects.using(destination).create(
            user_id=created.pk,
            email=created.email,
            is_annotator=True,
        )
        row["destination_id"] = created.pk
        report["created"] += 1
    return report


class Command(BaseCommand):
    help = (
        "Preview annotator-only transfer from ANNOTATION_SOURCE_DATABASE_URL "
        "to default. Copies no datasets, media, tokens, or staff privileges."
    )

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument(
            "--confirm-backup",
            action="store_true",
            help="Confirm a destination database backup exists.",
        )

    def handle(self, *args, **options):
        if options["apply"] and not options["confirm_backup"]:
            raise CommandError(
                "Back up the destination first, then pass --confirm-backup."
            )
        url = os.environ.get("ANNOTATION_SOURCE_DATABASE_URL", "").strip()
        if not url.startswith(("postgres://", "postgresql://")):
            raise CommandError(
                "Set ANNOTATION_SOURCE_DATABASE_URL to the private Neon URL."
            )
        alias = "annotation_transfer_source"
        config = copy.deepcopy(connections["default"].settings_dict)
        config.update(dj_database_url.parse(url, conn_max_age=0))
        connections.databases[alias] = config
        try:
            if any(connections[db].vendor != "postgresql" for db in (alias, "default")):
                raise CommandError("Both databases must be PostgreSQL.")
            with transaction.atomic(using=alias), transaction.atomic(using="default"):
                with connections[alias].cursor() as cursor:
                    cursor.execute(
                        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
                    )
                with connections["default"].cursor() as cursor:
                    if options["apply"]:
                        cursor.execute("SET LOCAL lock_timeout = '5s'")
                        table = connections["default"].ops.quote_name(
                            get_user_model()._meta.db_table
                        )
                        cursor.execute(
                            f"LOCK TABLE {table} IN SHARE ROW EXCLUSIVE MODE"
                        )
                    else:
                        cursor.execute(
                            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
                        )
                report = transfer_accounts(alias, "default", apply=options["apply"])
            self.stdout.write(json.dumps(report, indent=2))
            if options["apply"] and report["conflicts"]:
                raise CommandError(
                    "Transfer blocked by account conflicts. No accounts were created."
                )
        except CommandError:
            raise
        except Exception:
            raise CommandError(
                "Transfer failed; destination changes were rolled back. Check connectivity "
                "and schema migrations. Connection details are suppressed."
            ) from None
        finally:
            connections[alias].close()
            del connections[alias]
            del connections.databases[alias]
