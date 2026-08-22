"""Sales and court reports. Totals are server-side Decimal money."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone

from core.domain.pricing import money


def _range(start: date, end: date) -> tuple[datetime, datetime]:
    begin = timezone.make_aware(datetime.combine(start, time.min))
    finish = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min))
    return begin, finish


class ReportService:
    def sales_report(self, *, branch_id: int | None, start: date, end: date) -> dict:
        from apps.sales.models import Payment, Refund, Sale, SaleItem

        begin, finish = _range(start, end)
        sales = Sale.objects.filter(status=Sale.Status.COMPLETED, created_at__gte=begin, created_at__lt=finish)
        if branch_id:
            sales = sales.filter(branch_id=branch_id)

        totals = sales.aggregate(
            count=Count("id"),
            gross=Sum("gross_amount"),
            discount=Sum("discount_amount"),
            tax=Sum("tax_amount"),
            net=Sum("net_amount"),
        )
        refunds = Refund.objects.filter(created_at__gte=begin, created_at__lt=finish)
        if branch_id:
            refunds = refunds.filter(branch_id=branch_id)
        refund_total = refunds.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        payments = Payment.objects.filter(sale__in=sales).values("method").annotate(total=Sum("amount"), count=Count("id"))
        cashiers = (
            sales.values("cashier__username")
            .annotate(total=Sum("net_amount"), count=Count("id"))
            .order_by("-total")
        )
        products = (
            SaleItem.objects.filter(sale__in=sales)
            .values("name", "sku")
            .annotate(qty=Sum("quantity"), total=Sum("line_net"))
            .order_by("-total")[:20]
        )
        days = (
            sales.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("net_amount"), count=Count("id"))
            .order_by("day")
        )
        hours = (
            sales.annotate(hour=TruncHour("created_at"))
            .values("hour")
            .annotate(total=Sum("net_amount"), count=Count("id"))
            .order_by("hour")
        )
        hour_buckets = {h: {"label": f"{h:02d}:00", "total": Decimal("0.00"), "count": 0} for h in range(24)}
        for row in hours:
            if row["hour"] is None:
                continue
            hour_value = row["hour"]
            if timezone.is_naive(hour_value):
                hour_value = timezone.make_aware(hour_value)
            key = timezone.localtime(hour_value).hour
            hour_buckets[key]["total"] = money(row["total"] or 0)
            hour_buckets[key]["count"] = row["count"]

        net = money(totals["net"] or 0)
        return {
            "start": start,
            "end": end,
            "count": totals["count"] or 0,
            "gross": money(totals["gross"] or 0),
            "discount": money(totals["discount"] or 0),
            "tax": money(totals["tax"] or 0),
            "net": net,
            "refunds": money(refund_total),
            "net_after_refunds": money(net - refund_total),
            "payments": [
                {
                    "method": row["method"],
                    "label": dict(Payment.Method.choices).get(row["method"], row["method"]),
                    "total": money(row["total"] or 0),
                    "count": row["count"],
                }
                for row in payments
            ],
            "cashiers": [
                {
                    "name": row["cashier__username"] or "—",
                    "total": money(row["total"] or 0),
                    "count": row["count"],
                }
                for row in cashiers
            ],
            "products": [
                {
                    "name": row["name"],
                    "sku": row["sku"],
                    "qty": row["qty"] or 0,
                    "total": money(row["total"] or 0),
                }
                for row in products
            ],
            "days": [
                {"day": row["day"], "total": money(row["total"] or 0), "count": row["count"]}
                for row in days
            ],
            "hours": [hour_buckets[h] for h in range(8, 22)],
        }

    def court_report(self, *, branch_id: int | None, start: date, end: date) -> dict:
        from apps.courts.models import Booking, BookingRefund, Court

        begin, finish = _range(start, end)
        bookings = Booking.objects.filter(start_at__gte=begin, start_at__lt=finish).select_related("court")
        if branch_id:
            bookings = bookings.filter(branch_id=branch_id)
        courts = Court.objects.filter(is_active=True)
        if branch_id:
            courts = courts.filter(branch_id=branch_id)

        paid = bookings.filter(payment_status=Booking.PaymentStatus.PAID)
        cancelled = bookings.filter(status=Booking.Status.CANCELLED)
        refunds = BookingRefund.objects.filter(booking__start_at__gte=begin, booking__start_at__lt=finish)
        if branch_id:
            refunds = refunds.filter(branch_id=branch_id)

        paid_total = paid.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        refund_total = refunds.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        booked_hours = Decimal("0.00")
        court_rows: dict[int, dict] = {}
        hour_buckets = {h: {"label": f"{h:02d}:00", "count": 0, "total": Decimal("0.00")} for h in range(8, 22)}

        for booking in bookings:
            hours = Decimal(str(max((booking.end_at - booking.start_at).total_seconds() / 3600, 0)))
            row = court_rows.setdefault(
                booking.court_id,
                {
                    "name": booking.court.name,
                    "bookings": 0,
                    "cancelled": 0,
                    "hours": Decimal("0.00"),
                    "revenue": Decimal("0.00"),
                },
            )
            row["bookings"] += 1
            if booking.status == Booking.Status.CANCELLED:
                row["cancelled"] += 1
            if booking.status != Booking.Status.CANCELLED:
                row["hours"] += hours
                booked_hours += hours
            if booking.payment_status == Booking.PaymentStatus.PAID:
                row["revenue"] += booking.amount
            local_hour = timezone.localtime(booking.start_at).hour
            if local_hour in hour_buckets and booking.status != Booking.Status.CANCELLED:
                hour_buckets[local_hour]["count"] += 1
                hour_buckets[local_hour]["total"] += booking.amount if booking.payment_status == Booking.PaymentStatus.PAID else Decimal("0.00")

        days = max((end - start).days + 1, 1)
        capacity_hours = Decimal(courts.count() * 14 * days)
        utilization = money((booked_hours / capacity_hours) * 100) if capacity_hours else money(0)
        total_count = bookings.count()
        cancelled_count = cancelled.count()
        return {
            "start": start,
            "end": end,
            "bookings": total_count,
            "cancelled": cancelled_count,
            "refunds": money(refund_total),
            "revenue": money(paid_total),
            "net": money(paid_total),
            "hours": money(booked_hours),
            "capacity_hours": money(capacity_hours),
            "utilization": utilization,
            "cancellation_rate": money((Decimal(cancelled_count) / Decimal(total_count)) * 100) if total_count else money(0),
            "courts": sorted(
                [
                    {
                        "name": row["name"],
                        "bookings": row["bookings"],
                        "cancelled": row["cancelled"],
                        "hours": money(row["hours"]),
                        "revenue": money(row["revenue"]),
                    }
                    for row in court_rows.values()
                ],
                key=lambda row: row["revenue"],
                reverse=True,
            ),
            "hours_of_day": [
                {**hour_buckets[h], "total": money(hour_buckets[h]["total"])}
                for h in range(8, 22)
            ],
        }

    def inventory_report(self, *, branch_id: int | None, start: date, end: date) -> dict:
        from apps.inventory.models import InventoryBalance, InventoryMovement, MovementType
        from apps.products.models import Product
        from apps.sales.models import Sale, SaleItem
        from core.domain.inventory import EXPIRED, WASTAGE

        begin, finish = _range(start, end)
        products = Product.objects.filter(is_active=True, track_inventory=True).select_related("category")
        if branch_id:
            products = products.filter(branch_id=branch_id)
        balances = {
            (row.branch_id, row.product_id): row.quantity
            for row in InventoryBalance.objects.filter(product__in=products)
        }
        if branch_id:
            balances = {key: qty for key, qty in balances.items() if key[0] == branch_id}

        stock = []
        valuation = Decimal("0.00")
        low = []
        for product in products:
            qty = balances.get((product.branch_id, product.id), Decimal("0.000"))
            value = money(qty * product.cost_price)
            valuation += value
            row = {
                "name": product.name,
                "sku": product.sku,
                "category": product.category.name if product.category_id else "—",
                "qty": qty,
                "cost": money(product.cost_price),
                "value": value,
                "reorder": product.reorder_level,
                "is_low": bool(product.reorder_level and qty <= product.reorder_level),
            }
            stock.append(row)
            if row["is_low"]:
                low.append(row)

        movements = InventoryMovement.objects.filter(created_at__gte=begin, created_at__lt=finish).select_related("product")
        if branch_id:
            movements = movements.filter(branch_id=branch_id)
        type_rows = []
        wastage_value = Decimal("0.00")
        expired_value = Decimal("0.00")
        for row in movements.values("movement_type").annotate(count=Count("id"), qty=Sum("quantity")):
            type_rows.append(
                {
                    "type": row["movement_type"],
                    "label": dict(MovementType.choices).get(row["movement_type"], row["movement_type"]),
                    "count": row["count"],
                    "qty": row["qty"] or Decimal("0.000"),
                }
            )
        for movement in movements.filter(movement_type__in=[WASTAGE, EXPIRED]):
            value = money(abs(movement.quantity) * movement.unit_cost)
            if movement.movement_type == WASTAGE:
                wastage_value += value
            else:
                expired_value += value

        sold = (
            SaleItem.objects.filter(
                sale__status=Sale.Status.COMPLETED,
                sale__created_at__gte=begin,
                sale__created_at__lt=finish,
            )
            .values("sku", "name")
            .annotate(qty=Sum("quantity"), total=Sum("line_net"))
            .order_by("-qty")
        )
        if branch_id:
            sold = sold.filter(sale__branch_id=branch_id)
        sold_list = list(sold)
        sold_skus = {row["sku"] for row in sold_list}
        slow = [row for row in stock if row["sku"] not in sold_skus][:15]
        recent = list(movements.order_by("-created_at")[:40])
        return {
            "start": start,
            "end": end,
            "skus": len(stock),
            "on_hand_skus": sum(1 for row in stock if row["qty"] > 0),
            "valuation": money(valuation),
            "low_count": len(low),
            "wastage": money(wastage_value),
            "expired": money(expired_value),
            "stock": stock[:80],
            "low": low[:20],
            "types": type_rows,
            "fast": [
                {"name": row["name"], "sku": row["sku"], "qty": row["qty"] or 0, "total": money(row["total"] or 0)}
                for row in sold_list[:10]
            ],
            "slow": slow,
            "movements": recent,
        }

    def financial_report(self, *, branch_id: int | None, start: date, end: date) -> dict:
        from apps.expenses.models import Expense
        from apps.sales.models import Sale, SaleItem

        sales = self.sales_report(branch_id=branch_id, start=start, end=end)
        courts = self.court_report(branch_id=branch_id, start=start, end=end)
        begin, finish = _range(start, end)
        items = SaleItem.objects.filter(
            sale__status=Sale.Status.COMPLETED,
            sale__created_at__gte=begin,
            sale__created_at__lt=finish,
        ).select_related("product")
        if branch_id:
            items = items.filter(sale__branch_id=branch_id)
        cogs = Decimal("0.00")
        for item in items:
            cogs += money(item.quantity * item.product.cost_price)

        expenses = Expense.objects.filter(incurred_on__gte=start, incurred_on__lte=end)
        if branch_id:
            expenses = expenses.filter(branch_id=branch_id)
        expense_total = expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        by_category = (
            expenses.values("category__name")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )
        canteen_net = sales["net_after_refunds"]
        court_net = courts["revenue"]
        gross_profit = money(canteen_net - cogs + court_net)
        net_income = money(gross_profit - expense_total)
        return {
            "start": start,
            "end": end,
            "canteen_gross": sales["gross"],
            "canteen_discount": sales["discount"],
            "canteen_net": sales["net"],
            "canteen_refunds": sales["refunds"],
            "canteen_after_refunds": canteen_net,
            "court_revenue": court_net,
            "court_refunds": courts["refunds"],
            "cogs": money(cogs),
            "expenses": money(expense_total),
            "gross_profit": gross_profit,
            "net_income": net_income,
            "expense_rows": [
                {
                    "name": row["category__name"] or "Uncategorized",
                    "count": row["count"],
                    "total": money(row["total"] or 0),
                }
                for row in by_category
            ],
            "lines": [
                {"label": "Canteen net", "amount": sales["net"], "tone": "blue"},
                {"label": "Canteen refunds", "amount": sales["refunds"], "tone": "red"},
                {"label": "Court revenue", "amount": court_net, "tone": "purple"},
                {"label": "Cost of goods", "amount": money(cogs), "tone": "orange"},
                {"label": "Operating expenses", "amount": money(expense_total), "tone": "red"},
                {"label": "Estimated net income", "amount": net_income, "tone": "green"},
            ],
        }
