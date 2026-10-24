from django.db import migrations


def seed_cursor(apps, schema_editor):
    apps.get_model("care", "AssignmentRotation").objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    dependencies = [("care", "0004_onboarding_and_counselling")]
    operations = [migrations.RunPython(seed_cursor, migrations.RunPython.noop)]
