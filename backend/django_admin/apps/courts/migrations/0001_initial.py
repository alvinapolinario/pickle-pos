import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("branches", "0001_initial"),
        ("customers", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Court",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=20)),
                ("name", models.CharField(max_length=80)),
                ("status", models.CharField(choices=[("available", "Available"), ("maintenance", "Maintenance")], default="available", max_length=20)),
                ("hourly_rate", models.DecimalField(decimal_places=2, default=Decimal("350.00"), max_digits=14)),
                ("sort_order", models.PositiveIntegerField(default=10)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("branch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="courts", to="branches.branch")),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="CourtRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("weekday", models.PositiveSmallIntegerField(choices=[(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"), (4, "Friday"), (5, "Saturday"), (6, "Sunday")])),
                ("hourly_rate", models.DecimalField(decimal_places=2, max_digits=14)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("court", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rates", to="courts.court")),
            ],
            options={"ordering": ["court", "weekday"]},
        ),
        migrations.CreateModel(
            name="Booking",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("booking_number", models.CharField(max_length=50)),
                ("start_at", models.DateTimeField()),
                ("end_at", models.DateTimeField()),
                ("status", models.CharField(choices=[("confirmed", "Confirmed"), ("cancelled", "Cancelled"), ("completed", "Completed")], default="confirmed", max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14, validators=[django.core.validators.MinValueValidator(Decimal("0.00"))])),
                ("payment_method", models.CharField(blank=True, choices=[("cash", "Cash"), ("gcash", "GCash"), ("maya", "Maya"), ("bank_transfer", "Bank Transfer"), ("other", "Other")], max_length=20)),
                ("payment_status", models.CharField(choices=[("unpaid", "Unpaid"), ("paid", "Paid")], default="unpaid", max_length=20)),
                ("notes", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("booked_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="court_bookings", to=settings.AUTH_USER_MODEL)),
                ("branch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bookings", to="branches.branch")),
                ("court", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="bookings", to="courts.court")),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="bookings", to="customers.customer")),
            ],
            options={"ordering": ["start_at"]},
        ),
        migrations.AddConstraint(
            model_name="court",
            constraint=models.UniqueConstraint(fields=("branch", "code"), name="uniq_court_code_branch"),
        ),
        migrations.AddConstraint(
            model_name="courtrate",
            constraint=models.UniqueConstraint(fields=("court", "weekday"), name="uniq_court_rate_weekday"),
        ),
        migrations.AddConstraint(
            model_name="booking",
            constraint=models.UniqueConstraint(fields=("branch", "booking_number"), name="uniq_booking_number_branch"),
        ),
        migrations.AddConstraint(
            model_name="booking",
            constraint=models.CheckConstraint(condition=models.Q(("end_at__gt", models.F("start_at"))), name="booking_end_after_start"),
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(fields=["branch", "start_at"], name="courts_book_branch__idx"),
        ),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(fields=["court", "start_at"], name="courts_book_court_s_idx"),
        ),
    ]
