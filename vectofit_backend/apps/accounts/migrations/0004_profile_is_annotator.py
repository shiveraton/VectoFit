from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_profile_height_cm_profile_weight_kg"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="is_annotator",
            field=models.BooleanField(default=False),
        ),
    ]
