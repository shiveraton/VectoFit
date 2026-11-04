import django.db.models.deletion
from django.db import migrations, models


def copy_sample_annotators(apps, schema_editor):
    KneeAnnotation = apps.get_model("datasets", "KneeAnnotation")
    for record in KneeAnnotation.objects.select_related("sample").filter(
        annotator__isnull=True
    ):
        annotator_id = record.sample.annotator_id
        if annotator_id is not None:
            record.annotator_id = annotator_id
            record.save(update_fields=["annotator"])


class Migration(migrations.Migration):
    dependencies = [
        ("datasets", "0011_kneeannotation"),
    ]

    operations = [
        migrations.AlterField(
            model_name="kneeannotation",
            name="sample",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="knee_annotation_records",
                to="datasets.datasetsample",
            ),
        ),
        migrations.AlterField(
            model_name="kneeannotation",
            name="annotation",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="kneeannotation",
            name="annotator",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="knee_annotations",
                to="auth.user",
            ),
        ),
        migrations.AddField(
            model_name="kneeannotation",
            name="rubric_version",
            field=models.CharField(default="knee_v1", max_length=32),
        ),
        migrations.RemoveField(
            model_name="kneeannotation",
            name="updated_at",
        ),
        migrations.RunPython(copy_sample_annotators, migrations.RunPython.noop),
    ]
