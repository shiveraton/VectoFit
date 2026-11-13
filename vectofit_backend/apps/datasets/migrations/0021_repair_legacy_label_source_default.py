from typing import ClassVar

from django.db import migrations


def repair_legacy_label_source(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return
    table = apps.get_model("datasets", "DatasetSample")._meta.db_table
    with connection.cursor() as cursor:
        columns = connection.introspection.get_table_description(cursor, table)
    if any(column.name == "label_source" for column in columns):
        schema_editor.execute(
            f"ALTER TABLE {schema_editor.quote_name(table)} "
            "ALTER COLUMN \"label_source\" SET DEFAULT ''"
        )


class Migration(migrations.Migration):
    dependencies: ClassVar[list] = [
        ("datasets", "0020_repair_legacy_pipeline_config_hash_default"),
    ]

    operations: ClassVar[list] = [
        migrations.RunPython(repair_legacy_label_source, migrations.RunPython.noop),
    ]
