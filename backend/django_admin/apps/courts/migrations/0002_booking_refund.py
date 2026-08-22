import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("courts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="booking",
            name="payment_status",
            field=models.CharField(
                choices=[("unpaid", "Unpaid"), ("paid", "Paid"), ("refunded", "Refunded")],
                default="unpaid",
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="BookingRefund",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("refund_number", models.CharField(max_length=50)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))])),
                ("method", models.CharField(choices=[("cash", "Cash"), ("gcash", "GCash"), ("maya", "Maya"), ("bank_transfer", "Bank Transfer"), ("other", "Other")], default="cash", max_length=20)),
                ("reason", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("booking", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="refunds", to="courts.booking")),
                ("branch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="booking_refunds", to="branches.branch")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="booking_refunds", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="bookingrefund",
            constraint=models.UniqueConstraint(fields=("branch", "refund_number"), name="uniq_booking_refund_branch_number"),
        ),
    ]
