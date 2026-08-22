from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, F, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.branches.models import Branch
from apps.inventory.forms import MovementForm, StockCountForm
from apps.inventory.models import InventoryBalance, InventoryMovement
from apps.products.models import Product
from core.domain.exceptions import DomainError
from core.services.inventory_service import InventoryService


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


def _is_partial(request: HttpRequest) -> bool:
    return (
        request.GET.get("partial") == "1"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )


def _form_response(
    request: HttpRequest,
    form,
    *,
    title: str,
    action_url: str,
    list_url: str,
    status: int = 200,
) -> HttpResponse:
    context = {
        "form": form,
        "modal_title": title,
        "action_url": action_url,
        "list_url": list_url,
    }
    if _is_partial(request):
        return render(request, "console/partials/catalog_form.html", context, status=status)
    context.update(_page("stock", title, "Inventory"))
    return render(request, "console/catalog_form.html", context, status=status)


def _saved_response(request: HttpRequest, list_name: str, message: str) -> HttpResponse:
    messages.success(request, message)
    list_url = reverse(list_name)
    if _is_partial(request):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = list_url
        return response
    return redirect(list_url)


def _tracked_products(branch: Branch | None):
    products = Product.objects.filter(track_inventory=True, is_active=True).select_related(
        "category",
        "branch",
    )
    if branch:
        products = products.filter(branch=branch)
    balance = InventoryBalance.objects.filter(
        branch_id=OuterRef("branch_id"),
        product_id=OuterRef("pk"),
    ).values("quantity")[:1]
    return products.annotate(
        on_hand=Coalesce(
            Subquery(balance),
            Value(Decimal("0.000")),
            output_field=DecimalField(max_digits=12, decimal_places=3),
        )
    ).order_by("name")


@login_required
def stock_list(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "all")
    products = _tracked_products(branch)
    if q:
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(barcode__icontains=q))
    if status == "low":
        products = products.filter(reorder_level__gt=0, on_hand__lte=F("reorder_level"))
    elif status == "ok":
        products = products.filter(Q(reorder_level=0) | Q(on_hand__gt=F("reorder_level")))
    return render(
        request,
        "console/stock_list.html",
        _page(
            "stock",
            "Stock",
            "Current inventory balances by branch",
            {
                "products": products,
                "q": q,
                "status": status,
                "move_url": reverse("inventory:movement_create"),
                "count_url": reverse("inventory:stock_count"),
            },
        ),
    )


@login_required
def movement_list(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    q = request.GET.get("q", "").strip()
    movement_type = request.GET.get("type", "")
    movements = InventoryMovement.objects.select_related("product", "branch", "performed_by")
    if branch:
        movements = movements.filter(branch=branch)
    if q:
        movements = movements.filter(
            Q(product__name__icontains=q) | Q(product__sku__icontains=q) | Q(notes__icontains=q)
        )
    if movement_type:
        movements = movements.filter(movement_type=movement_type)
    return render(
        request,
        "console/stock_movements.html",
        _page(
            "stock_movements",
            "Stock Movements",
            "Append-only inventory ledger",
            {
                "movements": movements[:200],
                "q": q,
                "movement_type": movement_type,
                "move_url": reverse("inventory:movement_create"),
            },
        ),
    )


@login_required
def movement_create(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    initial = {}
    product_id = request.GET.get("product")
    if product_id:
        initial["product"] = product_id
    form = MovementForm(request.POST or None, branch=branch, initial=initial)
    if request.method == "POST" and form.is_valid():
        product = form.cleaned_data["product"]
        try:
            result = InventoryService().apply_movement(
                branch_id=product.branch_id,
                product_id=product.id,
                movement_type=form.cleaned_data["movement_type"],
                quantity=form.cleaned_data["quantity"],
                unit_cost=form.cleaned_data["unit_cost"] or Decimal("0.00"),
                reference_type="manual",
                performed_by_id=request.user.id,
                notes=form.cleaned_data["notes"],
            )
        except DomainError as exc:
            form.add_error(None, exc.message)
        else:
            return _saved_response(
                request,
                "inventory:stock_list",
                f"Recorded {result.quantity} for {product.name}. On hand is now {result.balance_after}.",
            )
    if request.method == "GET" and not _is_partial(request):
        query = "?modal=move"
        if product_id:
            query += f"&product={product_id}"
        return redirect(reverse("inventory:stock_list") + query)
    return _form_response(
        request,
        form,
        title="Record movement",
        action_url=reverse("inventory:movement_create"),
        list_url=reverse("inventory:stock_list"),
        status=422 if request.method == "POST" else 200,
    )


@login_required
def stock_count(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    initial: dict = {}
    product_id = request.GET.get("product")
    if product_id:
        initial["product"] = product_id
        if branch:
            initial["counted_quantity"] = InventoryService().get_on_hand(
                branch_id=branch.id,
                product_id=int(product_id),
            )
    form = StockCountForm(request.POST or None, branch=branch, initial=initial)
    if request.method == "POST" and form.is_valid():
        product = form.cleaned_data["product"]
        try:
            result = InventoryService().set_counted_quantity(
                branch_id=product.branch_id,
                product_id=product.id,
                counted_quantity=form.cleaned_data["counted_quantity"],
                performed_by_id=request.user.id,
                notes=form.cleaned_data["notes"],
            )
        except DomainError as exc:
            form.add_error(None, exc.message)
        else:
            return _saved_response(
                request,
                "inventory:stock_list",
                f"Counted {product.name}. On hand is now {result.balance_after}.",
            )
    if request.method == "GET" and not _is_partial(request):
        query = "?modal=count"
        if product_id:
            query += f"&product={product_id}"
        return redirect(reverse("inventory:stock_list") + query)
    return _form_response(
        request,
        form,
        title="Stock count",
        action_url=reverse("inventory:stock_count"),
        list_url=reverse("inventory:stock_list"),
        status=422 if request.method == "POST" else 200,
    )
