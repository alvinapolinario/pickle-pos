"""Offline sale push + catalog pull for the Android POS."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.domain.exceptions import DomainError, InsufficientStockError
from core.services.sale_service import PaymentInput, SaleLineInput, SaleService


@dataclass(frozen=True)
class SyncSaleInput:
    client_sale_uuid: UUID
    shift_id: int
    items: list[SaleLineInput]
    payments: list[PaymentInput]
    discount_amount: Decimal = Decimal("0.00")
    notes: str = ""
    hold: bool = False
    customer_id: int | None = None


@dataclass(frozen=True)
class SyncSaleResult:
    client_sale_uuid: str
    status: str
    sale_id: int | None
    message: str = ""


class SyncService:
    def record_sale(self, *, device_id: int, sale) -> None:
        from apps.sync.models import SyncTransaction

        SyncTransaction.objects.get_or_create(
            device_id=device_id,
            client_uuid=sale.client_sale_uuid,
            defaults={
                "server_entity_type": "sale",
                "server_entity_id": sale.id,
                "status": "synced",
            },
        )

    def push_sales(self, *, cashier_id: int, device_id: int, sales: list[SyncSaleInput]) -> list[SyncSaleResult]:
        results: list[SyncSaleResult] = []
        service = SaleService()
        for item in sales:
            try:
                sale = service.create_sale(
                    shift_id=item.shift_id,
                    cashier_id=cashier_id,
                    lines=item.items,
                    payments=[] if item.hold else item.payments,
                    discount_amount=item.discount_amount,
                    notes=item.notes,
                    device_id=device_id,
                    client_sale_uuid=item.client_sale_uuid,
                    hold=item.hold,
                    customer_id=item.customer_id,
                )
            except InsufficientStockError as exc:
                results.append(
                    SyncSaleResult(str(item.client_sale_uuid), "conflict", None, exc.message)
                )
                continue
            except DomainError as exc:
                results.append(
                    SyncSaleResult(str(item.client_sale_uuid), "rejected", None, exc.message)
                )
                continue
            self.record_sale(device_id=device_id, sale=sale)
            results.append(SyncSaleResult(str(item.client_sale_uuid), "synced", sale.id))
        return results

    def pull(self, *, branch_id: int | None, since: str | None = None) -> dict:
        from apps.products.models import BranchProductPrice, Category, Product

        cutoff = parse_datetime(since) if since else None
        if since and cutoff is None:
            raise DomainError("Invalid since cursor.")
        if cutoff and timezone.is_naive(cutoff):
            cutoff = timezone.make_aware(cutoff)

        categories = Category.objects.all()
        products = Product.objects.select_related("category").all()
        prices = BranchProductPrice.objects.all()
        if branch_id:
            categories = categories.filter(branch_id=branch_id)
            products = products.filter(branch_id=branch_id)
            prices = prices.filter(branch_id=branch_id)
        if cutoff:
            categories = categories.filter(updated_at__gte=cutoff)
            products = products.filter(updated_at__gte=cutoff)
            prices = prices.filter(updated_at__gte=cutoff)

        return {
            "cursor": timezone.now().isoformat(),
            "categories": [
                {
                    "id": category.id,
                    "branch_id": category.branch_id,
                    "name": category.name,
                    "sort_order": category.sort_order,
                    "is_active": category.is_active,
                }
                for category in categories.order_by("sort_order", "name")
            ],
            "products": [
                {
                    "id": product.id,
                    "branch_id": product.branch_id,
                    "category_id": product.category_id,
                    "sku": product.sku,
                    "barcode": product.barcode,
                    "name": product.name,
                    "selling_price": product.selling_price,
                    "cost_price": product.cost_price,
                    "unit": product.unit,
                    "tax_status": product.tax_status,
                    "track_inventory": product.track_inventory,
                    "is_active": product.is_active,
                }
                for product in products.order_by("name")
            ],
            "prices": [
                {
                    "branch_id": price.branch_id,
                    "product_id": price.product_id,
                    "selling_price": price.selling_price,
                }
                for price in prices
            ],
            "payment_methods": ["cash", "gcash", "maya", "bank_transfer", "other"],
            "tax": {"rate": "0.12", "inclusive": True},
        }
