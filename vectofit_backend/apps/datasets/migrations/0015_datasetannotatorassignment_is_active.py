from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("datasets", "0014_datasetannotatorassignment")]

    operations = [
        migrations.AddField(
            model_name="datasetannotatorassignment",
            name="is_active",
            field=models.BooleanField(
                default=True,
                help_text="Untick to revoke access without deleting the assignment or ratings.",
            ),
        ),
    ]
