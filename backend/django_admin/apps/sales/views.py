from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.branches.models import Branch
from apps.sales.forms import (
    RefundHeaderForm,
    SaleHeaderForm,
    make_payment_formset,
    make_refund_formset,
    make_sale_item_formset,
)
from apps.sales.models import Refund, Sale
from core.domain.exceptions import DomainError
from core.services.sale_service import PaymentInput, RefundLineInput, SaleLineInput, SaleService
from core.services.shift_service import ShiftService


def _page(page_name: str, title: str, subtitle: str, extra: dict | None = None) -> dict:
    context = {
        "page_name": page_name,
        "page_title": title,
        "page_subtitle": subtitle,
        "report_date": date.today(),
    }
    if extra:
        context.update(extra)
    return context


def _working_branch(request: HttpRequest) -> Branch | None:
    if request.user.branch_id:
        return request.user.branch
    return Branch.objects.filter(is_active=True).first()


def _is_partial(request: HttpRequest) -> bool:
    return request.GET.get("partial") == "1" or request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _form_response(request, template: str, context: dict, page_name: str, status: int = 200) -> HttpResponse:
    if _is_partial(request):
        return render(request, template, context, status=status)
    context["form_partial"] = template
    context.update(_page(page_name, context.get("modal_title", ""), "POS"))
    return render(request, "console/catalog_form.html", context, status=status)


def _saved(request, list_name: str, message: str) -> HttpResponse:
    messages.success(request, message)
    if _is_partial(request):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = reverse(list_name)
        return response
    return redirect(list_name)


def _current_shift(request, branch: Branch | None):
    return ShiftService().current_shift(
        cashier_id=request.user.id,
        branch_id=branch.id if branch else None,
    )


@login_required
def sale_list(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    shift = _current_shift(request, branch)
    q = request.GET.get("q", "").strip()
    sales = Sale.objects.select_related("cashier", "shift").order_by("-created_at")
    if branch:
        sales = sales.filter(branch=branch)
    if q:
        sales = sales.filter(Q(transaction_number__icontains=q) | Q(receipt_number__icontains=q))
    return render(
        request,
        "console/sale_list.html",
        _page(
            "sales",
            "Sales",
            "Create and review POS sales",
            {
                "sales": sales[:80],
                "q": q,
                "current_shift": shift,
                "create_url": reverse("sales:sale_create"),
                "hold_url": reverse("sales:sale_create") + "?hold=1",
            },
        ),
    )


@login_required
def transaction_list(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "all")
    sales = Sale.objects.select_related("cashier", "shift")
    if branch:
        sales = sales.filter(branch=branch)
    if q:
        sales = sales.filter(Q(transaction_number__icontains=q) | Q(receipt_number__icontains=q))
    if status != "all":
        sales = sales.filter(status=status)
    return render(
        request,
        "console/transaction_list.html",
        _page(
            "transactions",
            "Transactions",
            "All sales, voids, and payments",
            {"sales": sales[:200], "q": q, "status": status},
        ),
    )


def _sale_inputs(item_formset, payment_formset):
    lines = []
    for form in item_formset:
        data = getattr(form, "cleaned_data", None) or {}
        if not data or data.get("DELETE") or not data.get("product"):
            continue
        lines.append(SaleLineInput(data["product"].id, data["quantity"]))
    payments = []
    for form in payment_formset:
        data = getattr(form, "cleaned_data", None) or {}
        if not data or data.get("DELETE") or not data.get("amount"):
            continue
        payments.append(PaymentInput(data["method"], data["amount"], data.get("reference") or ""))
    return lines, payments


@login_required
def sale_create(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    shift = _current_shift(request, branch)
    hold = request.GET.get("hold") == "1" or request.POST.get("intent") == "hold"
    header = SaleHeaderForm(request.POST or None, branch=branch)
    items = make_sale_item_formset(branch, data=request.POST or None, prefix="items")
    payments = make_payment_formset(data=request.POST or None, prefix="payments")
    if request.method == "POST" and header.is_valid() and items.is_valid() and (hold or payments.is_valid()):
        try:
            if shift is None:
                raise DomainError("Open a shift before creating a sale.")
            lines, pay = _sale_inputs(items, payments)
            sale = SaleService().create_sale(
                shift_id=shift.id,
                cashier_id=request.user.id,
                lines=lines,
                payments=[] if hold else pay,
                discount_amount=header.cleaned_data.get("discount_amount") or Decimal("0.00"),
                notes=header.cleaned_data.get("notes") or "",
                hold=hold,
                customer_id=header.cleaned_data["customer"].id if header.cleaned_data.get("customer") else None,
            )
        except DomainError as exc:
            header.add_error(None, exc.message)
        else:
            label = "Held" if hold else sale.receipt_number
            return _saved(request, "sales:sale_list", f"{sale.transaction_number} {label}.")
    if request.method == "GET" and not _is_partial(request):
        query = "?modal=hold" if hold else "?modal=create"
        return redirect(reverse("sales:sale_list") + query)
    return _form_response(
        request,
        "console/partials/sale_form.html",
        {
            "form": header,
            "item_formset": items,
            "payment_formset": payments,
            "hold": hold,
            "modal_title": "Hold order" if hold else "New sale",
            "action_url": reverse("sales:sale_create") + ("?hold=1" if hold else ""),
            "list_url": reverse("sales:sale_list"),
            "submit_label": "Hold" if hold else "Complete sale",
        },
        "sales",
        status=422 if request.method == "POST" else 200,
    )


@login_required
def sale_resume(request: HttpRequest, pk: int) -> HttpResponse:
    sale = get_object_or_404(Sale, pk=pk)
    header = SaleHeaderForm(
        request.POST or None,
        branch=sale.branch,
        initial={"notes": sale.notes, "discount_amount": sale.discount_amount, "customer": sale.customer_id},
    )
    items = make_sale_item_formset(
        sale.branch,
        extra=0,
        data=None,
        prefix="items",
        initial=[{"product": item.product_id, "quantity": item.quantity} for item in sale.items.all()],
    )
    payments = make_payment_formset(data=request.POST or None, prefix="payments")
    if request.method == "POST" and payments.is_valid():
        try:
            _, pay = _sale_inputs(items, payments)
            completed = SaleService().resume_sale(sale_id=sale.id, cashier_id=request.user.id, payments=pay)
        except DomainError as exc:
            header.add_error(None, exc.message)
        else:
            return _saved(request, "sales:sale_list", f"{completed.transaction_number} completed.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("sales:sale_list") + f"?modal=resume&id={pk}")
    return _form_response(
        request,
        "console/partials/sale_form.html",
        {
            "form": header,
            "item_formset": items,
            "payment_formset": payments,
            "hold": False,
            "resume": True,
            "modal_title": f"Resume {sale.transaction_number}",
            "action_url": reverse("sales:sale_resume", args=[pk]),
            "list_url": reverse("sales:sale_list"),
            "submit_label": "Complete sale",
        },
        "sales",
        status=422 if request.method == "POST" else 200,
    )


@login_required
def sale_detail(request: HttpRequest, pk: int) -> HttpResponse:
    sale = get_object_or_404(
        Sale.objects.select_related("cashier", "shift", "branch", "customer").prefetch_related("items", "payments"),
        pk=pk,
    )
    if _is_partial(request) or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(request, "console/partials/sale_detail.html", {"sale": sale, "modal_title": sale.transaction_number})
    return redirect("sales:transaction_list")


@login_required
def sale_receipt(request: HttpRequest, pk: int) -> HttpResponse:
    from core.services.receipt_service import ReceiptService

    sale = get_object_or_404(
        Sale.objects.select_related("cashier", "shift", "branch", "customer").prefetch_related("items", "payments"),
        pk=pk,
    )
    receipt = ReceiptService().build(sale)
    if _is_partial(request) or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(
            request,
            "console/partials/receipt.html",
            {"sale": sale, "receipt": receipt, "modal_title": receipt.receipt_number or sale.transaction_number},
        )
    return render(
        request,
        "console/receipt_print.html",
        {"sale": sale, "receipt": receipt, "page_title": receipt.receipt_number or sale.transaction_number},
    )


@login_required
@require_POST
def sale_void(request: HttpRequest, pk: int) -> HttpResponse:
    try:
        sale = SaleService().void_sale(
            sale_id=pk,
            cashier_id=request.user.id,
            reason=request.POST.get("reason") or "Voided from console",
        )
    except DomainError as exc:
        messages.error(request, exc.message)
    else:
        messages.success(request, f"{sale.transaction_number} voided.")
    return redirect("sales:transaction_list")


@login_required
def sale_refund(request: HttpRequest, pk: int) -> HttpResponse:
    sale = get_object_or_404(Sale.objects.prefetch_related("items"), pk=pk)
    header = RefundHeaderForm(request.POST or None)
    initial = [
        {"sale_item_id": item.id, "quantity": Decimal("0")}
        for item in sale.items.all()
        if item.quantity_refundable > 0
    ]
    formset = make_refund_formset(
        data=request.POST or None,
        prefix="lines",
        initial=initial if request.method != "POST" else None,
    )
    if request.method != "POST":
        for form, item in zip(formset.forms, [i for i in sale.items.all() if i.quantity_refundable > 0], strict=False):
            form.product_name = item.name
            form.available = item.quantity_refundable
    else:
        items = {item.id: item for item in sale.items.all()}
        for form in formset.forms:
            try:
                item = items.get(int(form["sale_item_id"].value()))
            except (TypeError, ValueError):
                item = None
            if item:
                form.product_name = item.name
                form.available = item.quantity_refundable
    if request.method == "POST" and header.is_valid() and formset.is_valid():
        try:
            shift = _current_shift(request, sale.branch)
            if shift is None:
                raise DomainError("Open a shift before refunding.")
            lines = []
            for form in formset:
                data = getattr(form, "cleaned_data", None) or {}
                if data.get("sale_item_id") and data.get("quantity"):
                    lines.append(RefundLineInput(data["sale_item_id"], data["quantity"]))
            refund = SaleService().refund_sale(
                sale_id=sale.id,
                shift_id=shift.id,
                cashier_id=request.user.id,
                lines=lines,
                method=header.cleaned_data["method"],
                reason=header.cleaned_data.get("reason") or "",
            )
        except DomainError as exc:
            header.add_error(None, exc.message)
        else:
            return _saved(request, "sales:refund_list", f"{refund.refund_number} posted.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("sales:transaction_list") + f"?modal=refund&id={pk}")
    return _form_response(
        request,
        "console/partials/refund_form.html",
        {
            "form": header,
            "formset": formset,
            "sale": sale,
            "modal_title": f"Refund {sale.transaction_number}",
            "action_url": reverse("sales:sale_refund", args=[pk]),
            "list_url": reverse("sales:transaction_list"),
        },
        "refunds",
        status=422 if request.method == "POST" else 200,
    )


@login_required
def refund_list(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    refunds = Refund.objects.select_related("sale", "created_by", "shift")
    if branch:
        refunds = refunds.filter(branch=branch)
    return render(
        request,
        "console/refund_list.html",
        _page("refunds", "Refunds", "Process and review returns", {"refunds": refunds[:200]}),
    )
