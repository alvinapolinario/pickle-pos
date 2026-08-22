from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("branches", "0002_branch_vat_settings"),
    ]

    operations = [
        migrations.AddField(
            model_name="branch",
            name="memberships_enabled",
            field=models.BooleanField(default=True),
        ),
    ]
