from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.branches.models import Branch
from apps.products.models import Product
from apps.purchasing.models import Supplier
from core.services.purchasing_service import PurchaseLine, PurchasingService


SUPPLIERS = [
    ("Metro Beverage Dist.", "Ana Cruz", "0917-555-0101", "orders@metrobev.ph"),
    ("Sports Supply PH", "Luis Santos", "0918-555-0202", "purchasing@sportssupply.ph"),
    ("Local Market Co.", "Maya Lim", "0919-555-0303", ""),
]


class Command(BaseCommand):
    help = "Seed sample suppliers and an ordered purchase order for receiving"

    def handle(self, *args, **options):
        branch = Branch.objects.filter(is_active=True).order_by("id").first()
        if branch is None:
            self.stderr.write("No branch found. Run seed_rbac first.")
            return

        suppliers = []
        for name, contact, phone, email in SUPPLIERS:
            supplier, _ = Supplier.objects.update_or_create(
                branch=branch,
                name=name,
                defaults={
                    "contact_name": contact,
                    "phone": phone,
                    "email": email,
                    "is_active": True,
                },
            )
            suppliers.append(supplier)
            self.stdout.write(self.style.SUCCESS(f"Supplier: {supplier.name}"))

        drink = Product.objects.filter(branch=branch, sku="BEV-SD-500").first()
        water = Product.objects.filter(branch=branch, sku="BEV-WTR-500").first()
        if drink and water and not suppliers[0].purchase_orders.exists():
            po = PurchasingService().create_order(
                branch_id=branch.id,
                supplier_id=suppliers[0].id,
                created_by_id=None,
                expected_date=None,
                notes="Seeded opening replenishment",
                items=[
                    PurchaseLine(drink.id, Decimal("24"), drink.cost_price),
                    PurchaseLine(water.id, Decimal("36"), water.cost_price),
                ],
                submit=True,
            )
            self.stdout.write(self.style.SUCCESS(f"Purchase order: {po.po_number}"))

        self.stdout.write(self.style.SUCCESS("Purchasing seed complete"))
