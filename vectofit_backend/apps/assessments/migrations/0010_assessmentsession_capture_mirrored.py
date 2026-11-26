from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("assessments", "0009_repair_legacy_assessment_defaults")]
    operations = [migrations.AddField(
        model_name="assessmentsession", name="capture_mirrored",
        field=models.BooleanField(default=None, null=True),
    )]
