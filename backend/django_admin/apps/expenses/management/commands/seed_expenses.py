from django.core.management.base import BaseCommand

from apps.branches.models import Branch
from apps.expenses.models import ExpenseCategory

CATEGORIES = ["Rent", "Utilities", "Supplies", "Maintenance", "Wages"]


class Command(BaseCommand):
    help = "Seed expense categories for the active branch"

    def handle(self, *args, **options):
        branch = Branch.objects.filter(is_active=True).order_by("id").first()
        if branch is None:
            self.stderr.write("No branch found. Run seed_rbac first.")
            return
        for name in CATEGORIES:
            category, _ = ExpenseCategory.objects.update_or_create(
                branch=branch,
                name=name,
                defaults={"is_active": True},
            )
            self.stdout.write(self.style.SUCCESS(f"Category: {category.name}"))
        self.stdout.write(self.style.SUCCESS(f"Expense seed complete for {branch.name}"))
