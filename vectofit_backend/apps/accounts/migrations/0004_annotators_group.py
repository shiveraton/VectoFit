from django.db import migrations


def create_annotators_group(apps, schema_editor):
    apps.get_model("auth", "Group").objects.using(schema_editor.connection.alias).get_or_create(name="Annotators")


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_profile_height_cm_profile_weight_kg"), ("auth", "0012_alter_user_first_name_max_length")]
    operations = [migrations.RunPython(create_annotators_group, migrations.RunPython.noop)]
