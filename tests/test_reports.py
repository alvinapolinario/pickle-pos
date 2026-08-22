from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.courts.models import Court
from apps.expenses.models import Expense, ExpenseCategory
from apps.products.models import Category, Product, ProductUnit, TaxStatus
from core.domain.inventory import STOCK_IN, WASTAGE
from core.services.booking_service import BookingService
from core.services.inventory_service import InventoryService
from core.services.report_service import ReportService
from core.services.sale_service import PaymentInput, SaleLineInput, SaleService
from core.services.shift_service import ShiftService


@pytest.fixture
def stocked(branch):
    category = Category.objects.create(branch=branch, name="Drinks", sort_order=10)
    product = Product.objects.create(
        branch=branch,
        category=category,
        sku="BEV-SD-500",
        name="Sports Drink 500ml",
        selling_price=Decimal("45.00"),
        cost_price=Decimal("22.00"),
        unit=ProductUnit.BOTTLE,
        tax_status=TaxStatus.TAXABLE,
        track_inventory=True,
    )
    InventoryService().apply_movement(
        branch_id=branch.id,
        product_id=product.id,
        movement_type=STOCK_IN,
        quantity=Decimal("10"),
        unit_cost=product.cost_price,
        reference_type="opening",
    )
    return product


@pytest.mark.django_db
def test_sales_report_totals_tickets(branch, user, stocked):
    shift = ShiftService().open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("100.00"))
    SaleService().create_sale(
        shift_id=shift.id,
        cashier_id=user.id,
        lines=[SaleLineInput(stocked.id, Decimal("2"))],
        payments=[PaymentInput("cash", Decimal("90.00"))],
    )
    today = timezone.localdate()
    report = ReportService().sales_report(branch_id=branch.id, start=today, end=today)
    assert report["count"] == 1
    assert report["net"] == Decimal("90.00")
    assert report["products"][0]["name"] == "Sports Drink 500ml"
    assert report["cashiers"][0]["name"] == "cashier1"


@pytest.mark.django_db
def test_court_report_revenue_and_refund(branch, user):
    court = Court.objects.create(branch=branch, code="C1", name="Court 1", hourly_rate=Decimal("350.00"))
    start = (timezone.localtime() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=1)
    service = BookingService()
    booking = service.create_booking(court_id=court.id, booked_by_id=user.id, start_at=start, end_at=end)
    day = start.date()
    report = ReportService().court_report(branch_id=branch.id, start=day, end=day)
    assert report["bookings"] == 1
    assert report["revenue"] == Decimal("350.00")
    service.refund_booking(booking_id=booking.id, refunded_by_id=user.id)
    report = ReportService().court_report(branch_id=branch.id, start=day, end=day)
    assert report["revenue"] == Decimal("0.00")
    assert report["refunds"] == Decimal("350.00")
    assert report["cancelled"] == 1


@pytest.mark.django_db
def test_report_pages_render(django_client, user):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    sales = django_client.get(reverse("console:report_sales"))
    assert sales.status_code == 200
    assert b"Net sales" in sales.content
    courts = django_client.get(reverse("console:report_courts"))
    assert courts.status_code == 200
    assert b"Court revenue" in courts.content
    csv_sales = django_client.get(reverse("console:report_sales") + "?export=csv")
    assert csv_sales.status_code == 200
    assert "text/csv" in csv_sales["Content-Type"]
    pdf_sales = django_client.get(reverse("console:report_sales") + "?export=pdf")
    assert pdf_sales.status_code == 200
    assert pdf_sales["Content-Type"] == "application/pdf"
    assert pdf_sales.content.startswith(b"%PDF")
    pdf_fin = django_client.get(reverse("console:report_financial") + "?export=pdf")
    assert pdf_fin.status_code == 200
    assert pdf_fin.content.startswith(b"%PDF")
    assert django_client.get(reverse("console:report_inventory") + "?export=pdf").content.startswith(b"%PDF")
    assert django_client.get(reverse("console:report_courts") + "?export=pdf").content.startswith(b"%PDF")
    assert django_client.get(reverse("console:report_inventory")).status_code == 200
    assert django_client.get(reverse("console:report_financial")).status_code == 200
    assert django_client.get(reverse("expenses:expense_list")).status_code == 200


@pytest.mark.django_db
def test_inventory_report_values_and_wastage(branch, stocked):
    InventoryService().apply_movement(
        branch_id=branch.id,
        product_id=stocked.id,
        movement_type=WASTAGE,
        quantity=Decimal("1"),
        unit_cost=stocked.cost_price,
        reference_type="waste",
    )
    today = timezone.localdate()
    report = ReportService().inventory_report(branch_id=branch.id, start=today, end=today)
    assert report["skus"] == 1
    assert report["valuation"] == Decimal("198.00")
    assert report["wastage"] == Decimal("22.00")
    assert report["low_count"] == 0


@pytest.mark.django_db
def test_financial_report_subtracts_cogs_and_expenses(branch, user, stocked):
    shift = ShiftService().open_shift(cashier_id=user.id, branch_id=branch.id, opening_cash=Decimal("100.00"))
    SaleService().create_sale(
        shift_id=shift.id,
        cashier_id=user.id,
        lines=[SaleLineInput(stocked.id, Decimal("2"))],
        payments=[PaymentInput("cash", Decimal("90.00"))],
    )
    category = ExpenseCategory.objects.create(branch=branch, name="Rent")
    Expense.objects.create(branch=branch, category=category, amount=Decimal("30.00"), incurred_on=timezone.localdate())
    today = timezone.localdate()
    report = ReportService().financial_report(branch_id=branch.id, start=today, end=today)
    assert report["canteen_net"] == Decimal("90.00")
    assert report["cogs"] == Decimal("44.00")
    assert report["expenses"] == Decimal("30.00")
    assert report["gross_profit"] == Decimal("46.00")
    assert report["net_income"] == Decimal("16.00")
