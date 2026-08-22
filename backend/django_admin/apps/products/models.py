from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class TaxStatus(models.TextChoices):
    TAXABLE = "taxable", "Taxable"
    EXEMPT = "exempt", "VAT Exempt"


class ProductUnit(models.TextChoices):
    PIECE = "piece", "Piece"
    BOTTLE = "bottle", "Bottle"
    CAN = "can", "Can"
    PACK = "pack", "Pack"
    BOX = "box", "Box"
    SERVING = "serving", "Serving"


class Category(models.Model):
    """Branch-scoped product category for the POS catalog."""

    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.PROTECT,
        related_name="categories",
    )
    name = models.CharField(max_length=100)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "name"], name="uniq_category_branch_name"),
        ]
        indexes = [
            models.Index(fields=["branch", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    """Sellable catalog item. SKU is unique per branch."""

    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.PROTECT,
        related_name="products",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    sku = models.CharField(max_length=50)
    barcode = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    selling_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    cost_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    unit = models.CharField(max_length=20, choices=ProductUnit.choices, default=ProductUnit.PIECE)
    tax_status = models.CharField(max_length=20, choices=TaxStatus.choices, default=TaxStatus.TAXABLE)
    track_inventory = models.BooleanField(default=True)
    reorder_level = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0.000"),
        validators=[MinValueValidator(Decimal("0"))],
    )
    image = models.ImageField(upload_to="products/", blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "sku"], name="uniq_product_branch_sku"),
            models.UniqueConstraint(
                fields=["branch", "barcode"],
                condition=~models.Q(barcode=""),
                name="uniq_product_branch_barcode",
            ),
        ]
        indexes = [
            models.Index(fields=["branch", "is_active"]),
            models.Index(fields=["barcode"]),
            models.Index(fields=["sku"]),
        ]

    def clean(self) -> None:
        if self.category_id and self.branch_id and self.category.branch_id != self.branch_id:
            raise ValidationError({"category": "Category must belong to the same branch as the product."})

    def __str__(self) -> str:
        return f"{self.sku} — {self.name}"


class BranchProductPrice(models.Model):
    """Optional selling-price override for a product at a branch."""

    branch = models.ForeignKey(
        "branches.Branch",
        on_delete=models.CASCADE,
        related_name="product_prices",
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="branch_prices")
    selling_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["branch", "product"], name="uniq_branch_product_price"),
        ]

    def __str__(self) -> str:
        return f"{self.branch_id}:{self.product_id} @ {self.selling_price}"
