from typing import ClassVar

from django.db import migrations


def repair_legacy_pipeline_hash(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return
    table = apps.get_model("datasets", "Dataset")._meta.db_table
    with connection.cursor() as cursor:
        columns = connection.introspection.get_table_description(cursor, table)
    if any(column.name == "pipeline_config_hash" for column in columns):
        schema_editor.execute(
            f"ALTER TABLE {schema_editor.quote_name(table)} "
            "ALTER COLUMN \"pipeline_config_hash\" SET DEFAULT ''"
        )


class Migration(migrations.Migration):
    dependencies: ClassVar[list] = [("datasets", "0019_repair_kneeannotation_timestamp_default")]

    operations: ClassVar[list] = [
        migrations.RunPython(repair_legacy_pipeline_hash, migrations.RunPython.noop),
    ]
