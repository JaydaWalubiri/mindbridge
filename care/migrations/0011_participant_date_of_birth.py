from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("care", "0010_testing_profiles_and_keyword_details"),
    ]

    operations = [
        migrations.AddField(
            model_name="participant",
            name="date_of_birth",
            field=models.DateField(blank=True, null=True),
        ),
    ]
