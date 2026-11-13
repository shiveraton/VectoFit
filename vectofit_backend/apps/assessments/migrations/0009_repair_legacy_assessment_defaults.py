from typing import ClassVar

from django.db import migrations


def repair_legacy_assessment_defaults(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return
    defaults = {
        "landmark_schema_version": "'legacy_v1'",
        "missing_runs": "'[]'::jsonb",
        "pipeline_config_hash": "''",
        "feature_schema_version": "''",
    }
    for model_name in ("AssessmentSession", "RepAssessment"):
        table = apps.get_model("assessments", model_name)._meta.db_table
        with connection.cursor() as cursor:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(cursor, table)
            }
        for column, default in defaults.items():
            if column in columns:
                schema_editor.execute(
                    f"ALTER TABLE {schema_editor.quote_name(table)} "
                    f"ALTER COLUMN {schema_editor.quote_name(column)} SET DEFAULT {default}"
                )


class Migration(migrations.Migration):
    dependencies: ClassVar[list] = [
        ("assessments", "0006_repassessment_key_frame_index"),
    ]

    operations: ClassVar[list] = [
        migrations.RunPython(repair_legacy_assessment_defaults, migrations.RunPython.noop),
    ]
