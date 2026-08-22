from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.branches.models import Branch
from apps.products.models import Category, Product, ProductUnit, TaxStatus

CATEGORIES = [
    ("Drinks", 10),
    ("Snacks", 20),
    ("Sports Gear", 30),
    ("Accessories", 40),
]

PRODUCTS = [
    ("Drinks", "BEV-SD-500", "Sports Drink 500ml", "4801234560001", Decimal("45.00"), Decimal("22.00"), ProductUnit.BOTTLE, 20),
    ("Drinks", "BEV-WTR-500", "Bottled Water 500ml", "4801234560002", Decimal("25.00"), Decimal("10.00"), ProductUnit.BOTTLE, 24),
    ("Drinks", "BEV-COF-HOT", "Hot Coffee", "", Decimal("60.00"), Decimal("18.00"), ProductUnit.SERVING, 0),
    ("Snacks", "SNK-BAR-01", "Energy Bar", "4801234560003", Decimal("35.00"), Decimal("15.00"), ProductUnit.PIECE, 15),
    ("Snacks", "SNK-CHI-01", "Potato Chips", "4801234560004", Decimal("40.00"), Decimal("18.00"), ProductUnit.PACK, 12),
    ("Sports Gear", "BALL-OUT-YLW", "Pickleball Ball (Outdoor)", "4801234560005", Decimal("85.00"), Decimal("40.00"), ProductUnit.PIECE, 24),
    ("Sports Gear", "PADDLE-REC", "Recreational Paddle", "", Decimal("1500.00"), Decimal("900.00"), ProductUnit.PIECE, 4),
    ("Accessories", "ACC-GRIP-BK", "Grip Tape", "4801234560006", Decimal("75.00"), Decimal("30.00"), ProductUnit.PIECE, 10),
]


class Command(BaseCommand):
    help = "Seed sample categories and products for the active branch"

    def handle(self, *args, **options):
        branch = Branch.objects.filter(is_active=True).order_by("id").first()
        if branch is None:
            self.stderr.write("No branch found. Run seed_rbac first.")
            return

        category_map: dict[str, Category] = {}
        for name, sort_order in CATEGORIES:
            category, _ = Category.objects.update_or_create(
                branch=branch,
                name=name,
                defaults={"sort_order": sort_order, "is_active": True},
            )
            category_map[name] = category
            self.stdout.write(self.style.SUCCESS(f"Category: {category.name}"))

        for category_name, sku, name, barcode, price, cost, unit, reorder in PRODUCTS:
            track = reorder > 0
            product, _ = Product.objects.update_or_create(
                branch=branch,
                sku=sku,
                defaults={
                    "category": category_map[category_name],
                    "name": name,
                    "barcode": barcode,
                    "selling_price": price,
                    "cost_price": cost,
                    "unit": unit,
                    "tax_status": TaxStatus.TAXABLE,
                    "track_inventory": track,
                    "reorder_level": Decimal(reorder),
                    "is_active": True,
                },
            )
            self.stdout.write(self.style.SUCCESS(f"Product: {product.sku} — {product.name}"))

        self.stdout.write(self.style.SUCCESS(f"Catalog seed complete for {branch.name}"))
