from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("datasets", "0010_dataset_random_seed_dataset_review_count_and_more")]

    operations = [
        migrations.CreateModel(
            name="KneeAnnotation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("annotation", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("sample", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="knee_annotation_record", to="datasets.datasetsample")),
            ],
        ),
    ]
