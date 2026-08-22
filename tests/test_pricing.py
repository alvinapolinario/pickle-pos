from decimal import Decimal

import pytest

from apps.products.models import BranchProductPrice, Category, Product, ProductUnit, TaxStatus
from core.domain.exceptions import DomainError
from core.domain.pricing import PricingConfig, tax_amount
from core.services.pricing_service import PricingService, QuoteLineInput


@pytest.fixture
def category(branch):
    return Category.objects.create(branch=branch, name="Drinks", sort_order=10)


@pytest.fixture
def product(branch, category):
    return Product.objects.create(
        branch=branch,
        category=category,
        sku="BEV-VAT-112",
        name="VAT Inclusive Drink",
        selling_price=Decimal("112.00"),
        cost_price=Decimal("50.00"),
        unit=ProductUnit.BOTTLE,
        tax_status=TaxStatus.TAXABLE,
    )


def test_vat_inclusive_extracts_tax():
    tax = tax_amount(Decimal("112.00"), taxable=True, config=PricingConfig())
    assert tax == Decimal("12.00")


@pytest.mark.django_db
def test_quote_uses_server_price_and_vat(branch, product):
    quote = PricingService().quote(
        branch_id=branch.id,
        lines=[QuoteLineInput(product.id, Decimal("1"))],
    )
    assert quote.gross_amount == Decimal("112.00")
    assert quote.tax_amount == Decimal("12.00")
    assert quote.net_amount == Decimal("112.00")
    assert quote.lines[0].unit_price == Decimal("112.00")


@pytest.mark.django_db
def test_quote_applies_discount_then_tax(branch, product):
    quote = PricingService().quote(
        branch_id=branch.id,
        lines=[QuoteLineInput(product.id, Decimal("1"))],
        discount_amount=Decimal("12.00"),
    )
    assert quote.discount_amount == Decimal("12.00")
    assert quote.net_amount == Decimal("100.00")
    assert quote.tax_amount == Decimal("10.71")


@pytest.mark.django_db
def test_branch_price_override(branch, product):
    BranchProductPrice.objects.create(branch=branch, product=product, selling_price=Decimal("90.00"))
    quote = PricingService().quote(
        branch_id=branch.id,
        lines=[QuoteLineInput(product.id, Decimal("2"))],
    )
    assert quote.lines[0].unit_price == Decimal("90.00")
    assert quote.gross_amount == Decimal("180.00")


@pytest.mark.django_db
def test_quote_has_no_client_price_input(branch, product):
    fields = QuoteLineInput.__dataclass_fields__
    assert "unit_price" not in fields
    assert "line_total" not in fields
    quote = PricingService().quote(
        branch_id=branch.id,
        lines=[QuoteLineInput(product.id, Decimal("1"), Decimal("0.00"))],
    )
    assert quote.lines[0].unit_price == product.selling_price


@pytest.mark.django_db
def test_quote_skips_vat_when_branch_not_registered(branch, product):
    branch.vat_registered = False
    branch.save(update_fields=["vat_registered"])
    quote = PricingService().quote(
        branch_id=branch.id,
        lines=[QuoteLineInput(product.id, Decimal("1"))],
    )
    assert quote.tax_amount == Decimal("0.00")
    assert quote.net_amount == Decimal("112.00")
    assert quote.config.vat_registered is False


@pytest.mark.django_db
def test_discount_cannot_exceed_gross(branch, product):
    with pytest.raises(DomainError):
        PricingService().quote(
            branch_id=branch.id,
            lines=[QuoteLineInput(product.id, Decimal("1"))],
            discount_amount=Decimal("200.00"),
        )
