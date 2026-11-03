from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copy_existing_annotators(apps, schema_editor):
    KneeAnnotation = apps.get_model("datasets", "KneeAnnotation")
    DatasetSample = apps.get_model("datasets", "DatasetSample")
    for record in KneeAnnotation.objects.all().iterator():
        record.annotator_id = DatasetSample.objects.filter(
            pk=record.sample_id
        ).values_list("annotator_id", flat=True).first()
        record.save(update_fields=["annotator"])


class Migration(migrations.Migration):
    dependencies = [
        ("datasets", "0011_kneeannotation"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="kneeannotation",
            name="annotator",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="knee_annotations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="kneeannotation",
            name="sample",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="knee_annotations",
                to="datasets.datasetsample",
            ),
        ),
        migrations.RunPython(copy_existing_annotators, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="kneeannotation",
            constraint=models.UniqueConstraint(
                fields=("sample", "annotator"),
                name="unique_knee_annotation_per_annotator",
            ),
        ),
    ]
