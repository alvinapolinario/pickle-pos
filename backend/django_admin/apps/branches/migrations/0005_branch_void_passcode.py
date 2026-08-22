from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("branches", "0004_branch_receipt_header"),
    ]

    operations = [
        migrations.AddField(
            model_name="branch",
            name="void_passcode_hash",
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
