from django.db import migrations


def repair_legacy_timestamp(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return
    table = apps.get_model("datasets", "KneeAnnotation")._meta.db_table
    with connection.cursor() as cursor:
        columns = connection.introspection.get_table_description(cursor, table)
    if any(column.name == "updated_at" for column in columns):
        schema_editor.execute(
            f"ALTER TABLE {schema_editor.quote_name(table)} "
            'ALTER COLUMN "updated_at" SET DEFAULT CURRENT_TIMESTAMP'
        )


class Migration(migrations.Migration):
    dependencies = [("datasets", "0018_dataset_all_annotators_access")]

    operations = [
        migrations.RunPython(repair_legacy_timestamp, migrations.RunPython.noop),
    ]
