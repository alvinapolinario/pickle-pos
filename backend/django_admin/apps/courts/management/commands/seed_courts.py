from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.branches.models import Branch
from apps.courts.models import Court, CourtRate


COURTS = [
    ("C1", "Court 1", Decimal("350.00"), 10),
    ("C2", "Court 2", Decimal("350.00"), 20),
    ("C3", "Court 3", Decimal("400.00"), 30),
]


class Command(BaseCommand):
    help = "Seed sample courts and a weekend rate for the active branch"

    def handle(self, *args, **options):
        branch = Branch.objects.filter(is_active=True).order_by("id").first()
        if branch is None:
            self.stderr.write("No branch found. Run seed_rbac first.")
            return

        for code, name, rate, sort_order in COURTS:
            court, _ = Court.objects.update_or_create(
                branch=branch,
                code=code,
                defaults={
                    "name": name,
                    "hourly_rate": rate,
                    "sort_order": sort_order,
                    "status": Court.Status.AVAILABLE,
                    "is_active": True,
                },
            )
            self.stdout.write(self.style.SUCCESS(f"Court: {court.name}"))
            for weekday, weekend_rate in ((5, Decimal("450.00")), (6, Decimal("450.00"))):
                CourtRate.objects.update_or_create(
                    court=court,
                    weekday=weekday,
                    defaults={"hourly_rate": weekend_rate, "is_active": True},
                )

        self.stdout.write(self.style.SUCCESS(f"Court seed complete for {branch.name}"))
