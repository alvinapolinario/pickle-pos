from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("branches", "0003_branch_memberships_enabled"),
    ]

    operations = [
        migrations.AddField(
            model_name="branch",
            name="receipt_store_name",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="branch",
            name="receipt_address",
            field=models.TextField(blank=True),
        ),
    ]
