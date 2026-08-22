"""Server-authoritative product pricing. Never trust client unit prices or totals."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from core.domain.exceptions import DomainError
from core.domain.pricing import PricingConfig, line_gross, line_net, money, tax_amount


@dataclass(frozen=True)
class QuoteLineInput:
    product_id: int
    quantity: Decimal
    modifier_total: Decimal = Decimal("0.00")


@dataclass(frozen=True)
class PricedLine:
    product_id: int
    sku: str
    name: str
    quantity: Decimal
    unit_price: Decimal
    tax_status: str
    line_gross: Decimal
    line_discount: Decimal
    line_tax: Decimal
    line_net: Decimal
    track_inventory: bool
    cost_price: Decimal


@dataclass(frozen=True)
class TicketQuote:
    lines: tuple[PricedLine, ...]
    gross_amount: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    net_amount: Decimal
    config: PricingConfig = field(default_factory=PricingConfig)


class PricingService:
    def config_for_branch(self, branch) -> PricingConfig:
        registered = bool(getattr(branch, "vat_registered", True))
        rate = Decimal(str(getattr(branch, "tax_rate", Decimal("0.12")) or Decimal("0.12")))
        return PricingConfig(
            tax_rate=rate if registered else Decimal("0"),
            prices_include_tax=True,
            vat_registered=registered,
        )

    def unit_price(self, product, *, branch_id: int | None = None) -> Decimal:
        from apps.products.models import BranchProductPrice

        resolved_branch = branch_id or product.branch_id
        override = (
            BranchProductPrice.objects.filter(branch_id=resolved_branch, product_id=product.id).first()
            if resolved_branch
            else None
        )
        if override:
            return money(override.selling_price)
        return money(product.selling_price)

    def quote(
        self,
        *,
        branch_id: int,
        lines: list[QuoteLineInput],
        discount_amount: Decimal = Decimal("0.00"),
        config: PricingConfig | None = None,
    ) -> TicketQuote:
        from apps.branches.models import Branch
        from apps.products.models import Product

        if not lines:
            raise DomainError("Add at least one item.")

        branch = Branch.objects.filter(pk=branch_id).first()
        pricing = config or (self.config_for_branch(branch) if branch else PricingConfig())
        discount = money(discount_amount)
        if discount < 0:
            raise DomainError("Discount cannot be negative.")

        priced: list[PricedLine] = []
        for raw in lines:
            qty = Decimal(raw.quantity)
            if qty <= 0:
                raise DomainError("Quantity must be greater than zero.")
            product = Product.objects.filter(pk=raw.product_id, branch_id=branch_id).first()
            if product is None:
                raise DomainError("Product not found for this branch.")
            if not product.is_active:
                raise DomainError(f"{product.name} is inactive.")
            unit = self.unit_price(product, branch_id=branch_id) + money(raw.modifier_total)
            if unit < 0:
                raise DomainError("Unit price cannot be negative.")
            gross = line_gross(unit, qty)
            priced.append(
                PricedLine(
                    product_id=product.id,
                    sku=product.sku,
                    name=product.name,
                    quantity=qty,
                    unit_price=unit,
                    tax_status=product.tax_status,
                    line_gross=gross,
                    line_discount=money(0),
                    line_tax=money(0),
                    line_net=money(0),
                    track_inventory=product.track_inventory,
                    cost_price=money(product.cost_price),
                )
            )

        gross_total = money(sum((line.line_gross for line in priced), Decimal("0.00")))
        if discount > gross_total:
            raise DomainError("Discount cannot exceed the ticket total.")

        remaining = discount
        finalized: list[PricedLine] = []
        for index, line in enumerate(priced):
            if index == len(priced) - 1:
                share = remaining
            elif gross_total:
                share = money(line.line_gross / gross_total * discount)
                remaining = money(remaining - share)
            else:
                share = money(0)
            discounted_gross = money(line.line_gross - share)
            taxable = line.tax_status == "taxable"
            line_tax = tax_amount(discounted_gross, taxable=taxable, config=pricing)
            finalized.append(
                PricedLine(
                    product_id=line.product_id,
                    sku=line.sku,
                    name=line.name,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    tax_status=line.tax_status,
                    line_gross=line.line_gross,
                    line_discount=share,
                    line_tax=line_tax,
                    line_net=line_net(discounted_gross, line_tax, config=pricing),
                    track_inventory=line.track_inventory,
                    cost_price=line.cost_price,
                )
            )

        return TicketQuote(
            lines=tuple(finalized),
            gross_amount=gross_total,
            discount_amount=discount,
            tax_amount=money(sum((line.line_tax for line in finalized), Decimal("0.00"))),
            net_amount=money(sum((line.line_net for line in finalized), Decimal("0.00"))),
            config=pricing,
        )
