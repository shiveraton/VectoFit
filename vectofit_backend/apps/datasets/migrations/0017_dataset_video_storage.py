from django.db import migrations, models

import apps.datasets.storage


class Migration(migrations.Migration):
    dependencies = [("datasets", "0016_datasetassignmentevent")]
    operations = [
        migrations.AlterField(
            model_name="dataset", name="video_file",
            field=models.FileField(blank=True, null=True, upload_to="datasets/videos/", storage=apps.datasets.storage.dataset_video_storage),
        ),
        migrations.AlterField(
            model_name="datasetvideo", name="video_file",
            field=models.FileField(upload_to="dataset_video_upload_to", storage=apps.datasets.storage.dataset_video_storage),
        ),
    ]
