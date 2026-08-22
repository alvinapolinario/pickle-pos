import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("branches", "0003_branch_memberships_enabled"),
        ("customers", "0002_customer_loyalty_points"),
    ]

    operations = [
        migrations.CreateModel(
            name="MembershipTier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=20)),
                ("name", models.CharField(max_length=80)),
                (
                    "court_discount_pct",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=5,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0")),
                            django.core.validators.MaxValueValidator(Decimal("100")),
                        ],
                    ),
                ),
                (
                    "canteen_discount_pct",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=5,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0")),
                            django.core.validators.MaxValueValidator(Decimal("100")),
                        ],
                    ),
                ),
                ("priority_booking", models.BooleanField(default=False)),
                (
                    "points_per_peso",
                    models.DecimalField(
                        decimal_places=4,
                        default=Decimal("0.0000"),
                        help_text="Loyalty points earned per peso spent.",
                        max_digits=8,
                        validators=[django.core.validators.MinValueValidator(Decimal("0"))],
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="membership_tiers",
                        to="branches.branch",
                    ),
                ),
            ],
            options={
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="Membership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("started_on", models.DateField()),
                ("expires_on", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("expired", "Expired"), ("cancelled", "Cancelled")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("notes", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="memberships",
                        to="branches.branch",
                    ),
                ),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="memberships",
                        to="customers.customer",
                    ),
                ),
                (
                    "tier",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="memberships",
                        to="membership.membershiptier",
                    ),
                ),
            ],
            options={
                "ordering": ["-started_on", "-id"],
            },
        ),
        migrations.CreateModel(
            name="LoyaltyTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("points", models.IntegerField()),
                ("kind", models.CharField(choices=[("earn", "Earn"), ("reverse", "Reverse")], max_length=20)),
                ("source_type", models.CharField(max_length=40)),
                ("source_id", models.BigIntegerField()),
                ("notes", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="loyalty_transactions",
                        to="branches.branch",
                    ),
                ),
                (
                    "customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="loyalty_transactions",
                        to="customers.customer",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="membershiptier",
            constraint=models.UniqueConstraint(fields=("branch", "code"), name="uniq_membership_tier_branch_code"),
        ),
        migrations.AddIndex(
            model_name="membership",
            index=models.Index(fields=["branch", "status"], name="membership__branch_i_idx"),
        ),
        migrations.AddIndex(
            model_name="membership",
            index=models.Index(fields=["customer", "status"], name="membership__custome_idx"),
        ),
        migrations.AddIndex(
            model_name="loyaltytransaction",
            index=models.Index(fields=["customer", "created_at"], name="membership__cust_loy_idx"),
        ),
        migrations.AddIndex(
            model_name="loyaltytransaction",
            index=models.Index(fields=["source_type", "source_id"], name="membership__source_idx"),
        ),
    ]
