from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.branches.models import Branch
from apps.inventory.models import InventoryMovement
from apps.products.models import Product
from core.domain.inventory import STOCK_IN
from core.services.inventory_service import InventoryService


class Command(BaseCommand):
    help = "Seed opening stock for tracked catalog items that have no movements yet"

    def handle(self, *args, **options):
        branch = Branch.objects.filter(is_active=True).order_by("id").first()
        if branch is None:
            self.stderr.write("No branch found. Run seed_rbac first.")
            return

        service = InventoryService()
        products = Product.objects.filter(branch=branch, track_inventory=True, is_active=True)
        created = 0
        for product in products:
            if InventoryMovement.objects.filter(branch=branch, product=product).exists():
                continue
            opening = product.reorder_level * 2 if product.reorder_level > 0 else Decimal("10.000")
            service.apply_movement(
                branch_id=branch.id,
                product_id=product.id,
                movement_type=STOCK_IN,
                quantity=opening,
                unit_cost=product.cost_price,
                reference_type="opening",
                notes="Opening stock seed",
            )
            created += 1
            self.stdout.write(
                self.style.SUCCESS(f"{product.sku} opening stock {opening}")
            )

        self.stdout.write(self.style.SUCCESS(f"Inventory seed complete ({created} opening movements)"))
