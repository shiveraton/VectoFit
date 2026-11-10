from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("datasets", "0017_dataset_video_storage")]

    operations = [
        migrations.AddField(
            model_name="dataset",
            name="all_annotators_access",
            field=models.BooleanField(
                default=False,
                help_text="Allow all active annotator accounts to review this dataset.",
            ),
        ),
    ]
