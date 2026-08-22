"""Printable PDF reports from ReportService dicts. Sync generation — reports are small."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from fpdf import FPDF
from fpdf.enums import XPos, YPos


def _money(value) -> str:
    amount = Decimal(str(value or 0)).quantize(Decimal("0.01"))
    return f"PHP {amount:,.2f}"


def _text(value) -> str:
    if value is None:
        return "—"
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value.isoformat()
    return str(value)


class _ReportDoc(FPDF):
    def __init__(self, title: str, subtitle: str) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.report_title = title
        self.report_subtitle = subtitle
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(14, 18, 14)

    def header(self) -> None:
        self.set_fill_color(30, 138, 60)
        self.rect(0, 0, 210, 18, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 12)
        self.set_xy(14, 5)
        self.cell(0, 8, "PICKLEBALL POS", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(20, 30, 40)
        self.ln(6)
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 8, self.report_title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(80, 90, 100)
        self.cell(0, 6, self.report_subtitle, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(20, 30, 40)
        self.ln(3)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(120, 130, 140)
        self.cell(0, 8, f"Page {self.page_no()}/{{nb}}", align="C")

    def section(self, title: str) -> None:
        self.ln(2)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(30, 138, 60)
        self.cell(0, 7, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(20, 30, 40)

    def kpis(self, items: list[tuple[str, str]]) -> None:
        width = 182 / max(len(items), 1)
        self.set_font("Helvetica", "", 8)
        x = self.get_x()
        y = self.get_y()
        for index, (label, value) in enumerate(items):
            self.set_xy(x + index * width, y)
            self.set_fill_color(245, 248, 246)
            self.cell(width - 2, 14, "", fill=True)
            self.set_xy(x + index * width + 2, y + 1)
            self.set_font("Helvetica", "", 7)
            self.set_text_color(90, 100, 110)
            self.cell(width - 6, 4, label, new_x=XPos.LEFT, new_y=YPos.NEXT)
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(20, 30, 40)
            self.cell(width - 6, 6, value)
        self.set_xy(14, y + 16)
        self.ln(2)

    def table(self, headers: list[str], rows: list[list], widths: list[float] | None = None) -> None:
        if not headers:
            return
        usable = 182
        cols = widths or [usable / len(headers)] * len(headers)
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(30, 138, 60)
        self.set_text_color(255, 255, 255)
        for header, width in zip(headers, cols, strict=True):
            self.cell(width, 7, header, border=0, fill=True)
        self.ln()
        self.set_text_color(20, 30, 40)
        self.set_font("Helvetica", "", 8)
        if not rows:
            self.cell(usable, 7, "No rows for this range.")
            self.ln()
            return
        for index, row in enumerate(rows):
            if self.get_y() > 270:
                self.add_page()
                self.set_font("Helvetica", "B", 8)
                self.set_fill_color(30, 138, 60)
                self.set_text_color(255, 255, 255)
                for header, width in zip(headers, cols, strict=True):
                    self.cell(width, 7, header, border=0, fill=True)
                self.ln()
                self.set_text_color(20, 30, 40)
                self.set_font("Helvetica", "", 8)
            if index % 2:
                self.set_fill_color(245, 248, 246)
            else:
                self.set_fill_color(255, 255, 255)
            for value, width in zip(row, cols, strict=True):
                self.cell(width, 6, _text(value)[:40], fill=True)
            self.ln()


def _document(title: str, start: date, end: date, branch_name: str) -> _ReportDoc:
    subtitle = f"{branch_name}  |  {start.isoformat()} to {end.isoformat()}"
    pdf = _ReportDoc(title, subtitle)
    pdf.alias_nb_pages()
    pdf.add_page()
    return pdf


def _output(pdf: _ReportDoc) -> bytes:
    return bytes(pdf.output())


class ReportPdfService:
    def sales(self, report: dict, *, branch_name: str = "All branches") -> bytes:
        pdf = _document("Sales Report", report["start"], report["end"], branch_name)
        pdf.kpis(
            [
                ("Net sales", _money(report["net"])),
                ("Tickets", str(report["count"])),
                ("Discounts", _money(report["discount"])),
                ("After refunds", _money(report["net_after_refunds"])),
            ]
        )
        pdf.section("By day")
        pdf.table(
            ["Day", "Tickets", "Net"],
            [[row["day"], row["count"], _money(row["total"])] for row in report["days"]],
            [60, 40, 82],
        )
        pdf.section("Top products")
        pdf.table(
            ["Product", "SKU", "Qty", "Net"],
            [[row["name"], row["sku"], row["qty"], _money(row["total"])] for row in report["products"]],
            [80, 36, 26, 40],
        )
        pdf.section("Cashiers")
        pdf.table(
            ["Cashier", "Tickets", "Net"],
            [[row["name"], row["count"], _money(row["total"])] for row in report["cashiers"]],
            [80, 40, 62],
        )
        return _output(pdf)

    def courts(self, report: dict, *, branch_name: str = "All branches") -> bytes:
        pdf = _document("Court Report", report["start"], report["end"], branch_name)
        pdf.kpis(
            [
                ("Revenue", _money(report["revenue"])),
                ("Bookings", str(report["bookings"])),
                ("Utilization", f"{report['utilization']}%"),
                ("Cancel rate", f"{report['cancellation_rate']}%"),
            ]
        )
        pdf.section("By court")
        pdf.table(
            ["Court", "Bookings", "Cancelled", "Hours", "Revenue"],
            [
                [row["name"], row["bookings"], row["cancelled"], row["hours"], _money(row["revenue"])]
                for row in report["courts"]
            ],
            [50, 30, 32, 30, 40],
        )
        return _output(pdf)

    def inventory(self, report: dict, *, branch_name: str = "All branches") -> bytes:
        pdf = _document("Inventory Report", report["start"], report["end"], branch_name)
        pdf.kpis(
            [
                ("Stock value", _money(report["valuation"])),
                ("SKUs", str(report["skus"])),
                ("Low stock", str(report["low_count"])),
                ("Wastage", _money(report["wastage"])),
            ]
        )
        pdf.section("Stock snapshot")
        pdf.table(
            ["SKU", "Product", "On hand", "Cost", "Value", "Low"],
            [
                [
                    row["sku"],
                    row["name"],
                    row["qty"],
                    _money(row["cost"]),
                    _money(row["value"]),
                    "yes" if row["is_low"] else "",
                ]
                for row in report["stock"]
            ],
            [32, 52, 24, 26, 28, 20],
        )
        return _output(pdf)

    def financial(self, report: dict, *, branch_name: str = "All branches") -> bytes:
        pdf = _document("Financial Report", report["start"], report["end"], branch_name)
        pdf.kpis(
            [
                ("Est. net income", _money(report["net_income"])),
                ("Gross profit", _money(report["gross_profit"])),
                ("Expenses", _money(report["expenses"])),
                ("COGS", _money(report["cogs"])),
            ]
        )
        pdf.section("P and L")
        pdf.table(
            ["Line", "Amount"],
            [[row["label"], _money(row["amount"])] for row in report["lines"]],
            [120, 62],
        )
        pdf.section("Expenses by category")
        pdf.table(
            ["Category", "Count", "Amount"],
            [[row["name"], row["count"], _money(row["total"])] for row in report["expense_rows"]],
            [90, 32, 60],
        )
        return _output(pdf)
