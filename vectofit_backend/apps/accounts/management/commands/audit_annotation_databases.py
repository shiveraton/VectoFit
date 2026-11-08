"""Compare the configured local database with Neon without copying any rows."""

import copy
import json
import os
from contextlib import ExitStack

import dj_database_url
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction

from apps.accounts.models import Profile
from apps.datasets.models import (
    Dataset,
    DatasetAnnotatorAssignment,
    DatasetAssignmentEvent,
    DatasetSample,
    DatasetVideo,
    KneeAnnotation,
)


class Command(BaseCommand):
    help = (
        "Read-only comparison: default is the Supabase destination; "
        "ANNOTATION_SOURCE_DATABASE_URL supplies the Neon source."
    )

    def handle(self, *args, **options):
        source_url = os.environ.get("ANNOTATION_SOURCE_DATABASE_URL", "").strip()
        if not source_url.startswith(("postgres://", "postgresql://")):
            raise CommandError(
                "Set ANNOTATION_SOURCE_DATABASE_URL to the private Neon URL."
            )
        alias = "annotation_audit_source"
        config = copy.deepcopy(connections["default"].settings_dict)
        config.update(dj_database_url.parse(source_url, conn_max_age=0))
        connections.databases[alias] = config
        models = [
            get_user_model(),
            Profile,
            Dataset,
            DatasetVideo,
            DatasetSample,
            DatasetAnnotatorAssignment,
            DatasetAssignmentEvent,
            KneeAnnotation,
        ]
        try:
            with ExitStack() as stack:
                for database in ("default", alias):
                    if connections[database].vendor != "postgresql":
                        raise CommandError("Both databases must be PostgreSQL.")
                    stack.enter_context(transaction.atomic(using=database))
                    with connections[database].cursor() as cursor:
                        cursor.execute(
                            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"
                        )
                report = {}
                for label, database in (("destination", "default"), ("source", alias)):
                    report[label] = {
                        model._meta.label: model.objects.using(database).count()
                        for model in models
                    }
                User = get_user_model()
                source_users = list(
                    User.objects.using(alias).values_list("username", "email")
                )
                destination_users = list(
                    User.objects.using("default").values_list("username", "email")
                )
                names = {name for name, _ in destination_users}
                emails = {email.casefold() for _, email in destination_users if email}
                report["potential_account_conflicts"] = {
                    "same_username": sum(name in names for name, _ in source_users),
                    "same_email_ignoring_case": sum(
                        bool(email) and email.casefold() in emails
                        for _, email in source_users
                    ),
                }
                report["notes"] = [
                    "No rows were modified. No connection strings or passwords are included.",
                    "Matching numeric IDs do not establish matching identities or datasets.",
                    "Dataset, video and sample identities must be mapped before migrating ratings.",
                    "This report is not a backup and does not confirm media file availability.",
                ]
            self.stdout.write(json.dumps(report, indent=2))
        except CommandError:
            raise
        except Exception:
            raise CommandError(
                "Audit failed. Check database connectivity and schema migrations on both "
                "databases. No database error details are printed to protect credentials."
            ) from None
        finally:
            connections[alias].close()
            del connections[alias]
            del connections.databases[alias]
