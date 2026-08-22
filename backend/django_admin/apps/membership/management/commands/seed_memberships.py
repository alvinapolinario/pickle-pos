from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.branches.models import Branch
from apps.membership.models import MembershipTier

TIERS = [
    ("REGULAR", "Regular", Decimal("0"), Decimal("0"), Decimal("0.0000"), False, 10),
    ("STUDENT", "Student", Decimal("10"), Decimal("5"), Decimal("0.0500"), False, 20),
    ("PREMIUM", "Premium", Decimal("15"), Decimal("10"), Decimal("0.1000"), True, 30),
    ("CLUB", "Club", Decimal("20"), Decimal("15"), Decimal("0.1500"), True, 40),
]


class Command(BaseCommand):
    help = "Seed default membership tiers for the active branch"

    def handle(self, *args, **options):
        branch = Branch.objects.filter(is_active=True).order_by("id").first()
        if branch is None:
            self.stderr.write("No branch found. Run seed_rbac first.")
            return
        for code, name, court, canteen, points, priority, sort in TIERS:
            MembershipTier.objects.update_or_create(
                branch=branch,
                code=code,
                defaults={
                    "name": name,
                    "court_discount_pct": court,
                    "canteen_discount_pct": canteen,
                    "points_per_peso": points,
                    "priority_booking": priority,
                    "sort_order": sort,
                    "is_active": True,
                },
            )
            self.stdout.write(self.style.SUCCESS(f"Seeded tier: {name}"))
        self.stdout.write(self.style.SUCCESS("Membership seed complete"))
