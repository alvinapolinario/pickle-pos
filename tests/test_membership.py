from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.customers.models import Customer
from apps.membership.models import MembershipTier
from apps.products.models import Category, Product, ProductUnit
from core.domain.inventory import STOCK_IN
from core.services.booking_service import BookingService
from core.services.inventory_service import InventoryService
from core.services.membership_service import MembershipService
from core.services.pricing_service import PricingService, QuoteLineInput
from core.services.sale_service import PaymentInput, SaleLineInput, SaleService
from core.services.shift_service import ShiftService
from apps.courts.models import Court


@pytest.fixture
def product(branch):
    category = Category.objects.create(branch=branch, name="Drinks", sort_order=10)
    item = Product.objects.create(
        branch=branch,
        category=category,
        sku="MEM-SD-500",
        name="Member Drink",
        selling_price=Decimal("100.00"),
        cost_price=Decimal("40.00"),
        unit=ProductUnit.BOTTLE,
        track_inventory=True,
    )
    InventoryService().apply_movement(
        branch_id=branch.id,
        product_id=item.id,
        movement_type=STOCK_IN,
        quantity=Decimal("20"),
        reference_type="opening",
    )
    return item


@pytest.fixture
def premium(branch):
    return MembershipTier.objects.create(
        branch=branch,
        code="PREMIUM",
        name="Premium",
        court_discount_pct=Decimal("20.00"),
        canteen_discount_pct=Decimal("10.00"),
        points_per_peso=Decimal("0.1000"),
        priority_booking=True,
    )


@pytest.fixture
def member(branch, premium):
    customer = Customer.objects.create(branch=branch, name="Mia Santos", mobile="09170009999")
    MembershipService().assign(branch_id=branch.id, customer_id=customer.id, tier_id=premium.id)
    return customer


@pytest.mark.django_db
def test_canteen_membership_discount(branch, product, member):
    quote = PricingService().quote(
        branch_id=branch.id,
        lines=[QuoteLineInput(product.id, Decimal("1"))],
        customer_id=member.id,
    )
    assert quote.discount_amount == Decimal("10.00")
    assert quote.net_amount == Decimal("90.00")


@pytest.mark.django_db
def test_membership_flag_turns_discounts_off(branch, product, member):
    branch.memberships_enabled = False
    branch.save(update_fields=["memberships_enabled"])
    quote = PricingService().quote(
        branch_id=branch.id,
        lines=[QuoteLineInput(product.id, Decimal("1"))],
        customer_id=member.id,
    )
    assert quote.discount_amount == Decimal("0.00")
    assert quote.net_amount == Decimal("100.00")


@pytest.mark.django_db
def test_sale_earns_and_void_reverses_points(branch, user, product, member):
    shift = ShiftService().open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("200"))
    sale = SaleService().create_sale(
        shift_id=shift.id,
        cashier_id=user.id,
        lines=[SaleLineInput(product.id, Decimal("1"))],
        payments=[PaymentInput("cash", Decimal("90.00"))],
        customer_id=member.id,
    )
    member.refresh_from_db()
    assert sale.discount_amount == Decimal("10.00")
    assert member.loyalty_points == 9
    SaleService().void_sale(sale_id=sale.id, cashier_id=user.id, reason="test")
    member.refresh_from_db()
    assert member.loyalty_points == 0


@pytest.mark.django_db
def test_court_membership_discount(branch, user, member):
    court = Court.objects.create(branch=branch, code="C9", name="Court 9", hourly_rate=Decimal("400.00"))
    start = (timezone.localtime() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)
    quoted = BookingService().quote(court_id=court.id, start_at=start, end_at=end, customer_id=member.id)
    assert quoted["amount"] == Decimal("320.00")
    booking = BookingService().create_booking(
        court_id=court.id,
        booked_by_id=user.id,
        start_at=start,
        end_at=end,
        customer_id=member.id,
        payment_method="cash",
    )
    assert booking.amount == Decimal("320.00")
    member.refresh_from_db()
    assert member.loyalty_points == 32


@pytest.mark.django_db
def test_membership_console_lists(django_client, user, premium):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    response = django_client.get(reverse("membership:membership_list"))
    assert response.status_code == 200
    assert b"Premium" in response.content
    assert b"New tier" in response.content
