"""Live dashboard figures from sales, inventory, shifts, and courts."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from apps.console.sparkline import sparkline_points
from core.domain.pricing import money
from core.domain.shifts import OPEN


def _peso(value) -> str:
    return f"₱ {money(value or 0):,.2f}"


def _delta(today, yesterday) -> tuple[str, str]:
    today = money(today or 0)
    yesterday = money(yesterday or 0)
    if yesterday == 0:
        return ("—", "vs yesterday") if today == 0 else ("new", "vs yesterday")
    pct = ((today - yesterday) / yesterday) * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%", "vs yesterday"


def dashboard_data(branch=None) -> dict:
    from apps.courts.models import Booking
    from apps.expenses.models import Expense
    from apps.inventory.models import InventoryBalance
    from apps.products.models import Product
    from apps.sales.models import Payment, Sale
    from apps.shifts.models import CashierShift
    from core.services.booking_service import BookingService

    now = timezone.localtime()
    today = now.date()
    yesterday = today - timedelta(days=1)
    month_start = today.replace(day=1)

    sales = Sale.objects.filter(status=Sale.Status.COMPLETED)
    if branch:
        sales = sales.filter(branch=branch)

    today_sales = sales.filter(created_at__date=today)
    yesterday_sales = sales.filter(created_at__date=yesterday)
    month_sales = sales.filter(created_at__date__gte=month_start)

    today_total = today_sales.aggregate(total=Sum("net_amount"))["total"] or Decimal("0.00")
    yesterday_total = yesterday_sales.aggregate(total=Sum("net_amount"))["total"] or Decimal("0.00")
    today_count = today_sales.count()
    yesterday_count = yesterday_sales.count()
    today_tax = today_sales.aggregate(total=Sum("tax_amount"))["total"] or Decimal("0.00")
    from apps.sales.models import SaleItem

    today_cost = Decimal("0.00")
    for row in SaleItem.objects.filter(sale__in=today_sales).select_related("product"):
        today_cost += money(row.product.cost_price * row.quantity)
    gross_profit = money(today_total - today_cost)

    sales_delta, sales_label = _delta(today_total, yesterday_total)
    count_delta, _ = _delta(today_count, yesterday_count)
    profit_delta, _ = _delta(gross_profit, 0)

    spark = []
    overview_labels = []
    overview_total = []
    for offset in range(9, -1, -1):
        day = today - timedelta(days=offset)
        day_total = sales.filter(created_at__date=day).aggregate(total=Sum("net_amount"))["total"] or 0
        spark.append(float(day_total))
        if offset < 7:
            overview_labels.append(day.strftime("%b %d"))
            overview_total.append(float(day_total))

    payments_qs = Payment.objects.filter(sale__in=today_sales)
    pay_map = {method: Decimal("0.00") for method, _ in Payment.Method.choices}
    for row in payments_qs.values("method").annotate(total=Sum("amount")):
        pay_map[row["method"]] = money(row["total"])
    pay_total = sum(pay_map.values(), Decimal("0.00")) or Decimal("1.00")
    colors = {
        "cash": "#16a34a",
        "gcash": "#2563eb",
        "maya": "#06b6d4",
        "bank_transfer": "#f59e0b",
        "other": "#94a3b8",
    }
    slices = []
    for method, label in Payment.Method.choices:
        amount = pay_map[method]
        if amount <= 0 and method == "other":
            continue
        slices.append(
            {
                "label": label,
                "value": round(float(amount / pay_total * 100), 1) if pay_total else 0,
                "amount": _peso(amount),
                "color": colors.get(method, "#94a3b8"),
            }
        )

    recent = []
    for sale in today_sales.select_related("cashier").order_by("-created_at")[:8]:
        recent.append(
            {
                "id": sale.receipt_number or sale.transaction_number,
                "type": "Canteen",
                "kind": "canteen",
                "amount": _peso(sale.net_amount),
                "time": timezone.localtime(sale.created_at).strftime("%I:%M %p"),
            }
        )

    products = Product.objects.filter(track_inventory=True, is_active=True)
    if branch:
        products = products.filter(branch=branch)
    low_stock = []
    for product in products.order_by("name")[:20]:
        balance = InventoryBalance.objects.filter(product=product, branch=product.branch).first()
        qty = balance.quantity if balance else Decimal("0")
        if product.reorder_level and qty <= product.reorder_level:
            low_stock.append(
                {
                    "name": product.name,
                    "sku": product.sku,
                    "qty": float(qty),
                    "min": float(product.reorder_level),
                    "tone": "drink",
                    "percent": round(float(qty / product.reorder_level * 100)) if product.reorder_level else 0,
                }
            )
    low_stock = low_stock[:6]

    shifts = []
    open_shifts = CashierShift.objects.filter(status=OPEN).select_related("cashier")
    if branch:
        open_shifts = open_shifts.filter(branch=branch)
    for shift in open_shifts[:8]:
        name = shift.cashier.get_full_name() or shift.cashier.username
        parts = name.split()
        initials = "".join(p[0] for p in parts[:2]).upper() if parts else name[:2].upper()
        shifts.append(
            {
                "name": name,
                "initials": initials,
                "open_time": timezone.localtime(shift.opened_at).strftime("%I:%M %p"),
                "opening_cash": _peso(shift.opening_cash),
            }
        )

    month_total = month_sales.aggregate(total=Sum("net_amount"))["total"] or 0
    month_discount = month_sales.aggregate(total=Sum("discount_amount"))["total"] or 0
    expense_qs = Expense.objects.filter(incurred_on__gte=month_start, incurred_on__lte=today)
    if branch:
        expense_qs = expense_qs.filter(branch=branch)
    month_expenses = expense_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    court_qs = Booking.objects.exclude(status=Booking.Status.CANCELLED)
    if branch:
        court_qs = court_qs.filter(branch=branch)
    today_court = court_qs.filter(start_at__date=today, payment_status=Booking.PaymentStatus.PAID)
    yesterday_court = court_qs.filter(start_at__date=yesterday, payment_status=Booking.PaymentStatus.PAID)
    today_court_total = today_court.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    yesterday_court_total = yesterday_court.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    month_court = court_qs.filter(start_at__date__gte=month_start, payment_status=Booking.PaymentStatus.PAID).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    month_net = money(Decimal(month_total or 0) + Decimal(month_court or 0) - month_expenses)
    court_spark = []
    court_overview = []
    for offset in range(9, -1, -1):
        day = today - timedelta(days=offset)
        day_total = court_qs.filter(start_at__date=day, payment_status=Booking.PaymentStatus.PAID).aggregate(total=Sum("amount"))["total"] or 0
        court_spark.append(float(day_total))
        if offset < 7:
            court_overview.append(float(day_total))
    court_delta, court_delta_label = _delta(today_court_total, yesterday_court_total)

    occ = BookingService().occupancy(branch_id=branch.id if branch else None)
    occ_total = occ["total"] or 1
    occupancy = {
        "percent": round(occ["occupied"] / occ_total * 100) if occ["total"] else 0,
        "slices": [
            {"label": "Occupied", "value": round(occ["occupied"] / occ_total * 100, 1) if occ["total"] else 0, "detail": f"{occ['occupied']} in play", "color": "#7c3aed"},
            {"label": "Available", "value": round(occ["available"] / occ_total * 100, 1) if occ["total"] else 100, "detail": f"{occ['available']} open", "color": "#16a34a"},
            {"label": "Maintenance", "value": round(occ["maintenance"] / occ_total * 100, 1) if occ["total"] else 0, "detail": f"{occ['maintenance']} closed", "color": "#94a3b8"},
        ],
    }
    if not occ["total"]:
        occupancy = {
            "percent": 0,
            "slices": [{"label": "Available", "value": 100, "detail": "No courts yet", "color": "#e2e8f0"}],
        }

    upcoming = []
    for booking in court_qs.filter(status=Booking.Status.CONFIRMED, end_at__gte=now).select_related("court", "customer").order_by("start_at")[:6]:
        upcoming.append(
            {
                "slot": f"{timezone.localtime(booking.start_at).strftime('%I:%M %p')} – {timezone.localtime(booking.end_at).strftime('%I:%M %p')}",
                "court": booking.court.name,
                "customer": booking.customer.name if booking.customer_id else "Walk-in",
            }
        )

    kpis = [
        {
            "key": "total",
            "label": "Total Sales",
            "period": "Today",
            "value": _peso(today_total),
            "delta": sales_delta,
            "delta_label": sales_label,
            "tone": "green",
            "sparkline": spark,
            "sparkline_points": sparkline_points(spark),
        },
        {
            "key": "canteen",
            "label": "Canteen Sales",
            "period": "Today",
            "value": _peso(today_total),
            "delta": sales_delta,
            "delta_label": sales_label,
            "tone": "blue",
            "sparkline": spark,
            "sparkline_points": sparkline_points(spark),
        },
        {
            "key": "court",
            "label": "Court Revenue",
            "period": "Today",
            "value": _peso(today_court_total),
            "delta": court_delta,
            "delta_label": court_delta_label,
            "tone": "purple",
            "sparkline": court_spark,
            "sparkline_points": sparkline_points(court_spark),
        },
        {
            "key": "transactions",
            "label": "Transactions",
            "period": "Today",
            "value": str(today_count),
            "delta": count_delta,
            "delta_label": "vs yesterday",
            "tone": "orange",
            "sparkline": spark,
            "sparkline_points": sparkline_points(spark or [0]),
        },
        {
            "key": "profit",
            "label": "Gross Profit",
            "period": "Today",
            "value": _peso(gross_profit),
            "delta": profit_delta,
            "delta_label": "est. vs cost",
            "tone": "teal",
            "sparkline": spark,
            "sparkline_points": sparkline_points(spark),
        },
    ]

    return {
        "kpis": kpis,
        "sales_overview": {
            "labels": overview_labels or [today.strftime("%b %d")],
            "total": overview_total or [0],
            "canteen": overview_total or [0],
            "court": court_overview or [0] * len(overview_total or [0]),
        },
        "payments": {"total": _peso(sum(pay_map.values(), Decimal("0.00"))), "slices": slices or [
            {"label": "Cash", "value": 100, "amount": _peso(0), "color": "#16a34a"}
        ]},
        "occupancy": occupancy,
        "transactions": recent,
        "low_stock": low_stock,
        "shifts": shifts,
        "bookings": upcoming,
        "financial": [
            {"label": "Total Sales", "value": _peso(month_total), "tone": "blue"},
            {"label": "Discounts", "value": _peso(month_discount), "tone": "red"},
            {"label": "Expenses", "value": _peso(month_expenses), "tone": "red"},
            {"label": "Est. net income", "value": _peso(month_net), "tone": "green"},
        ],
        "notification_count": len(low_stock),
        "is_demo": False,
        "court_placeholder": occ["total"] == 0,
    }
