from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("assessments", "0005_assessmentsession_view_angle")]

    operations = [
        migrations.AddField(
            model_name="repassessment",
            name="key_frame_index",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Representative source-video frame, normally the segmented squat bottom.",
                null=True,
            ),
        ),
    ]
