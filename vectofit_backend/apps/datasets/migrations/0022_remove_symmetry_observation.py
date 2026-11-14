from django.db import migrations


def remove_symmetry_observation(apps, schema_editor):
    KneeAnnotation = apps.get_model("datasets", "KneeAnnotation")
    manager = KneeAnnotation.objects.using(schema_editor.connection.alias)
    records = manager.only("pk", "annotation").iterator(chunk_size=500)

    for record in records:
        if not isinstance(record.annotation, dict):
            continue
        if "symmetry_observation" not in record.annotation:
            continue

        annotation = dict(record.annotation)
        annotation.pop("symmetry_observation")
        manager.filter(pk=record.pk).update(annotation=annotation)


class Migration(migrations.Migration):
    dependencies = [("datasets", "0021_repair_legacy_label_source_default")]

    operations = [
        migrations.RunPython(remove_symmetry_observation, migrations.RunPython.noop),
    ]