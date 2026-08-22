from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.branches.models import Branch
from apps.purchasing.forms import (
    PurchaseOrderForm,
    ReceiveOrderForm,
    SupplierForm,
    make_item_formset,
    make_receive_formset,
)
from apps.purchasing.models import PurchaseOrder, PurchaseReceipt, Supplier
from core.domain.exceptions import DomainError
from core.domain.purchasing import RECEIVABLE_STATUSES
from core.services.purchasing_service import PurchaseLine, PurchasingService, ReceiveLine


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
    branch_id = request.GET.get("branch") or request.POST.get("branch_id")
    if branch_id:
        return Branch.objects.filter(pk=branch_id, is_active=True).first()
    return Branch.objects.filter(is_active=True).first()


def _lock_branch(request: HttpRequest) -> bool:
    return bool(request.user.branch_id)


def _is_partial(request: HttpRequest) -> bool:
    return (
        request.GET.get("partial") == "1"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )


def _form_response(request, template: str, context: dict, list_url: str, status: int = 200) -> HttpResponse:
    if _is_partial(request):
        return render(request, template, context, status=status)
    context["form_partial"] = template
    context.update(_page(context.get("page_name", "purchase_orders"), context.get("modal_title", ""), "Purchasing"))
    return render(request, "console/catalog_form.html", context, status=status)


def _saved_response(request: HttpRequest, list_name: str, message: str) -> HttpResponse:
    messages.success(request, message)
    list_url = reverse(list_name)
    if _is_partial(request):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = list_url
        return response
    return redirect(list_url)


def _lines_from_formset(formset) -> list[PurchaseLine]:
    lines = []
    for form in formset:
        data = getattr(form, "cleaned_data", None) or {}
        if not data or data.get("DELETE") or not data.get("product"):
            continue
        lines.append(
            PurchaseLine(
                product_id=data["product"].id,
                quantity_ordered=data["quantity_ordered"],
                unit_cost=data.get("unit_cost") or Decimal("0.00"),
            )
        )
    return lines


def _receive_lines_from_formset(formset) -> list[ReceiveLine]:
    lines = []
    for form in formset:
        data = getattr(form, "cleaned_data", None) or {}
        if not data or not data.get("purchase_item_id"):
            continue
        qty = data.get("quantity") or Decimal("0")
        if qty <= 0:
            continue
        lines.append(
            ReceiveLine(
                purchase_item_id=data["purchase_item_id"],
                quantity=qty,
                unit_cost=data.get("unit_cost"),
            )
        )
    return lines


@login_required
def supplier_list(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "active")
    suppliers = Supplier.objects.select_related("branch")
    if branch:
        suppliers = suppliers.filter(branch=branch)
    if q:
        suppliers = suppliers.filter(
            Q(name__icontains=q) | Q(contact_name__icontains=q) | Q(phone__icontains=q)
        )
    if status == "active":
        suppliers = suppliers.filter(is_active=True)
    elif status == "inactive":
        suppliers = suppliers.filter(is_active=False)
    return render(
        request,
        "console/supplier_list.html",
        _page(
            "suppliers",
            "Suppliers",
            "Vendor records and contacts",
            {
                "suppliers": suppliers,
                "q": q,
                "status": status,
                "create_url": reverse("purchasing:supplier_create"),
            },
        ),
    )


@login_required
def supplier_create(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    form = SupplierForm(request.POST or None, branch=branch, lock_branch=_lock_branch(request))
    if request.method == "POST" and form.is_valid():
        supplier = form.save(commit=False)
        if _lock_branch(request):
            supplier.branch = request.user.branch
        supplier.save()
        return _saved_response(request, "purchasing:supplier_list", f"Supplier “{supplier.name}” created.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("purchasing:supplier_list") + "?modal=create")
    return _form_response(
        request,
        "console/partials/catalog_form.html",
        {
            "form": form,
            "modal_title": "New supplier",
            "action_url": reverse("purchasing:supplier_create"),
            "list_url": reverse("purchasing:supplier_list"),
            "page_name": "suppliers",
        },
        reverse("purchasing:supplier_list"),
        status=422 if request.method == "POST" else 200,
    )


@login_required
def supplier_edit(request: HttpRequest, pk: int) -> HttpResponse:
    supplier = get_object_or_404(Supplier, pk=pk)
    form = SupplierForm(
        request.POST or None,
        instance=supplier,
        branch=supplier.branch,
        lock_branch=_lock_branch(request),
    )
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        if _lock_branch(request):
            saved.branch = request.user.branch
        saved.save()
        return _saved_response(request, "purchasing:supplier_list", f"Supplier “{saved.name}” updated.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("purchasing:supplier_list") + f"?modal=edit&id={pk}")
    return _form_response(
        request,
        "console/partials/catalog_form.html",
        {
            "form": form,
            "modal_title": f"Edit {supplier.name}",
            "action_url": reverse("purchasing:supplier_edit", args=[pk]),
            "list_url": reverse("purchasing:supplier_list"),
            "page_name": "suppliers",
        },
        reverse("purchasing:supplier_list"),
        status=422 if request.method == "POST" else 200,
    )


@login_required
@require_POST
def supplier_toggle(request: HttpRequest, pk: int) -> HttpResponse:
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier.is_active = not supplier.is_active
    supplier.save(update_fields=["is_active", "updated_at"])
    state = "activated" if supplier.is_active else "deactivated"
    messages.success(request, f"Supplier “{supplier.name}” {state}.")
    return redirect("purchasing:supplier_list")


@login_required
def purchase_order_list(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "open")
    orders = PurchaseOrder.objects.select_related("supplier", "branch").annotate(
        received_qty=Sum("items__quantity_received"),
        ordered_total=Sum(
            ExpressionWrapper(
                F("items__quantity_ordered") * F("items__unit_cost"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        ),
    )
    if branch:
        orders = orders.filter(branch=branch)
    if q:
        orders = orders.filter(Q(po_number__icontains=q) | Q(supplier__name__icontains=q))
    if status == "open":
        orders = orders.filter(status__in=["draft", "ordered", "partial"])
    elif status != "all":
        orders = orders.filter(status=status)
    return render(
        request,
        "console/purchase_order_list.html",
        _page(
            "purchase_orders",
            "Purchase Orders",
            "Create and track purchase orders",
            {
                "orders": orders,
                "q": q,
                "status": status,
                "create_url": reverse("purchasing:purchase_order_create"),
            },
        ),
    )


def _po_form_context(request, *, po, form, formset, title, action_url):
    return {
        "form": form,
        "formset": formset,
        "modal_title": title,
        "action_url": action_url,
        "list_url": reverse("purchasing:purchase_order_list"),
        "page_name": "purchase_orders",
        "submit_label": "Save & submit" if not po or po.can_edit else "Save",
        "show_submit": po is None or po.can_edit,
    }


@login_required
def purchase_order_create(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    form = PurchaseOrderForm(request.POST or None, branch=branch)
    formset = make_item_formset(branch, data=request.POST or None, prefix="items")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        try:
            po = PurchasingService().create_order(
                branch_id=form.cleaned_data["supplier"].branch_id,
                supplier_id=form.cleaned_data["supplier"].id,
                created_by_id=request.user.id,
                expected_date=form.cleaned_data.get("expected_date"),
                notes=form.cleaned_data.get("notes") or "",
                items=_lines_from_formset(formset),
                submit=request.POST.get("intent") == "submit",
            )
        except DomainError as exc:
            form.add_error(None, exc.message)
        else:
            verb = "submitted" if po.status != "draft" else "saved"
            return _saved_response(request, "purchasing:purchase_order_list", f"{po.po_number} {verb}.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("purchasing:purchase_order_list") + "?modal=create")
    return _form_response(
        request,
        "console/partials/po_form.html",
        _po_form_context(
            request,
            po=None,
            form=form,
            formset=formset,
            title="New purchase order",
            action_url=reverse("purchasing:purchase_order_create"),
        ),
        reverse("purchasing:purchase_order_list"),
        status=422 if request.method == "POST" else 200,
    )


@login_required
def purchase_order_edit(request: HttpRequest, pk: int) -> HttpResponse:
    po = get_object_or_404(PurchaseOrder.objects.select_related("supplier"), pk=pk)
    if not po.can_edit:
        messages.error(request, "Only draft purchase orders can be edited.")
        return redirect("purchasing:purchase_order_list")
    initial_items = [
        {
            "product": item.product_id,
            "quantity_ordered": item.quantity_ordered,
            "unit_cost": item.unit_cost,
        }
        for item in po.items.select_related("product")
    ]
    form = PurchaseOrderForm(
        request.POST or None,
        branch=po.branch,
        initial={
            "supplier": po.supplier_id,
            "expected_date": po.expected_date,
            "notes": po.notes,
        },
    )
    formset = make_item_formset(
        po.branch,
        data=request.POST or None,
        prefix="items",
        initial=initial_items if request.method != "POST" else None,
    )
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        try:
            saved = PurchasingService().update_draft(
                po_id=po.id,
                supplier_id=form.cleaned_data["supplier"].id,
                expected_date=form.cleaned_data.get("expected_date"),
                notes=form.cleaned_data.get("notes") or "",
                items=_lines_from_formset(formset),
                submit=request.POST.get("intent") == "submit",
            )
        except DomainError as exc:
            form.add_error(None, exc.message)
        else:
            verb = "submitted" if saved.status != "draft" else "updated"
            return _saved_response(request, "purchasing:purchase_order_list", f"{saved.po_number} {verb}.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("purchasing:purchase_order_list") + f"?modal=edit&id={pk}")
    return _form_response(
        request,
        "console/partials/po_form.html",
        _po_form_context(
            request,
            po=po,
            form=form,
            formset=formset,
            title=f"Edit {po.po_number}",
            action_url=reverse("purchasing:purchase_order_edit", args=[pk]),
        ),
        reverse("purchasing:purchase_order_list"),
        status=422 if request.method == "POST" else 200,
    )


@login_required
def purchase_order_detail(request: HttpRequest, pk: int) -> HttpResponse:
    po = get_object_or_404(
        PurchaseOrder.objects.select_related("supplier", "branch", "created_by"),
        pk=pk,
    )
    items = po.items.select_related("product")
    receipts = po.receipts.select_related("received_by").prefetch_related("items__product")
    returns = po.returns.select_related("returned_by").prefetch_related("items__product")
    context = {
        "po": po,
        "items": items,
        "receipts": receipts,
        "returns": returns,
        "modal_title": po.po_number,
    }
    if _is_partial(request):
        return render(request, "console/partials/po_detail.html", context)
    return redirect("purchasing:purchase_order_list")


@login_required
@require_POST
def purchase_order_cancel(request: HttpRequest, pk: int) -> HttpResponse:
    try:
        po = PurchasingService().cancel_order(po_id=pk)
    except DomainError as exc:
        messages.error(request, exc.message)
    else:
        messages.success(request, f"{po.po_number} cancelled.")
    return redirect("purchasing:purchase_order_list")


def _receivable_orders(branch: Branch | None):
    orders = PurchaseOrder.objects.select_related("supplier").filter(status__in=RECEIVABLE_STATUSES)
    if branch:
        orders = orders.filter(branch=branch)
    return orders.order_by("-created_at")


def _receive_formset_for(po: PurchaseOrder | None, post=None, *, returning: bool = False):
    initial = []
    if po:
        for item in po.items.select_related("product"):
            available = item.quantity_received if returning else item.quantity_outstanding
            if available <= 0:
                continue
            initial.append(
                {
                    "purchase_item_id": item.id,
                    "quantity": available,
                    "unit_cost": item.unit_cost,
                    "product_name": str(item.product),
                    "available": available,
                }
            )
    formset = make_receive_formset(data=post, prefix="lines", initial=initial if post is None else None)
    if po and post is None:
        for form, row in zip(formset.forms, initial, strict=False):
            form.product_name = row["product_name"]
            form.available = row["available"]
    elif po:
        items = {item.id: item for item in po.items.select_related("product")}
        for form in formset.forms:
            item_id = form["purchase_item_id"].value()
            try:
                item = items.get(int(item_id))
            except (TypeError, ValueError):
                item = None
            if item:
                form.product_name = str(item.product)
                form.available = item.quantity_received if returning else item.quantity_outstanding
    return formset


@login_required
def receive_create(request: HttpRequest, pk: int | None = None) -> HttpResponse:
    branch = _working_branch(request)
    receivable = _receivable_orders(branch)
    po = get_object_or_404(PurchaseOrder, pk=pk) if pk else None
    if po is not None and po.status not in RECEIVABLE_STATUSES:
        messages.error(request, "Only ordered purchase orders can be received.")
        return redirect("purchasing:purchase_order_list")
    if po is None:
        po_id = request.GET.get("po") or request.POST.get("purchase_order")
        if po_id:
            po = receivable.filter(pk=po_id).first() or get_object_or_404(PurchaseOrder, pk=po_id)
    header = ReceiveOrderForm(
        request.POST or None,
        queryset=receivable,
        lock_po=pk is not None,
        initial={"purchase_order": po} if po else None,
    )
    formset = _receive_formset_for(po, request.POST or None)
    if request.method == "POST" and header.is_valid() and formset.is_valid() and po:
        try:
            receipt = PurchasingService().receive(
                po_id=po.id,
                lines=_receive_lines_from_formset(formset),
                received_by_id=request.user.id,
                notes=header.cleaned_data.get("notes") or "",
            )
        except DomainError as exc:
            header.add_error(None, exc.message)
        else:
            return _saved_response(
                request,
                "purchasing:receiving_list",
                f"{receipt.receipt_number} posted for {po.po_number}.",
            )
    list_name = "purchasing:purchase_order_list" if pk else "purchasing:receiving_list"
    if request.method == "GET" and not _is_partial(request):
        if pk:
            return redirect(reverse("purchasing:purchase_order_list") + f"?modal=receive&id={pk}")
        query = "?modal=receive"
        if request.GET.get("po"):
            query += f"&po={request.GET['po']}"
        return redirect(reverse("purchasing:receiving_list") + query)
    action = (
        reverse("purchasing:purchase_order_receive", args=[pk])
        if pk
        else reverse("purchasing:receive_create")
    )
    return _form_response(
        request,
        "console/partials/receive_form.html",
        {
            "form": header,
            "formset": formset,
            "po": po,
            "returning": False,
            "modal_title": f"Receive {po.po_number}" if po else "Receive stock",
            "action_url": action,
            "list_url": reverse(list_name),
            "page_name": "receiving",
            "submit_label": "Post receipt",
        },
        reverse(list_name),
        status=422 if request.method == "POST" else 200,
    )


@login_required
def return_create(request: HttpRequest, pk: int) -> HttpResponse:
    po = get_object_or_404(PurchaseOrder.objects.select_related("supplier"), pk=pk)
    header = ReceiveOrderForm(
        request.POST or None,
        queryset=PurchaseOrder.objects.filter(pk=pk),
        lock_po=True,
        initial={"purchase_order": po, "notes": ""},
    )
    formset = _receive_formset_for(po, request.POST or None, returning=True)
    if request.method == "POST" and header.is_valid() and formset.is_valid():
        try:
            ret = PurchasingService().return_to_supplier(
                po_id=po.id,
                lines=_receive_lines_from_formset(formset),
                returned_by_id=request.user.id,
                notes=header.cleaned_data.get("notes") or "",
            )
        except DomainError as exc:
            header.add_error(None, exc.message)
        else:
            return _saved_response(
                request,
                "purchasing:purchase_order_list",
                f"{ret.return_number} posted for {po.po_number}.",
            )
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("purchasing:purchase_order_list") + f"?modal=return&id={pk}")
    return _form_response(
        request,
        "console/partials/receive_form.html",
        {
            "form": header,
            "formset": formset,
            "po": po,
            "returning": True,
            "modal_title": f"Return {po.po_number}",
            "action_url": reverse("purchasing:purchase_order_return", args=[pk]),
            "list_url": reverse("purchasing:purchase_order_list"),
            "page_name": "purchase_orders",
            "submit_label": "Post return",
        },
        reverse("purchasing:purchase_order_list"),
        status=422 if request.method == "POST" else 200,
    )


@login_required
def receiving_list(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    q = request.GET.get("q", "").strip()
    receipts = PurchaseReceipt.objects.select_related(
        "purchase_order",
        "purchase_order__supplier",
        "received_by",
        "branch",
    ).annotate(qty=Sum("items__quantity"))
    if branch:
        receipts = receipts.filter(branch=branch)
    if q:
        receipts = receipts.filter(
            Q(receipt_number__icontains=q)
            | Q(purchase_order__po_number__icontains=q)
            | Q(purchase_order__supplier__name__icontains=q)
        )
    return render(
        request,
        "console/receiving_list.html",
        _page(
            "receiving",
            "Receiving",
            "Receive stock against purchase orders",
            {
                "receipts": receipts,
                "q": q,
                "create_url": reverse("purchasing:receive_create"),
            },
        ),
    )
