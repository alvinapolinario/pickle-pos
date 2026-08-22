from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.branches.models import Branch
from apps.products.forms import CategoryForm, ProductForm
from apps.products.models import Category, Product


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


def _form_response(
    request: HttpRequest,
    form,
    *,
    kind: str,
    title: str,
    action_url: str,
    list_url: str,
    status: int = 200,
) -> HttpResponse:
    context = {
        "form": form,
        "kind": kind,
        "modal_title": title,
        "action_url": action_url,
        "list_url": list_url,
    }
    if _is_partial(request):
        return render(request, "console/partials/catalog_form.html", context, status=status)
    context.update(_page(kind, title, "Catalog"))
    return render(request, "console/catalog_form.html", context, status=status)


def _saved_response(request: HttpRequest, list_name: str, message: str) -> HttpResponse:
    messages.success(request, message)
    list_url = reverse(list_name)
    if _is_partial(request):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = list_url
        return response
    return redirect(list_url)


@login_required
def category_list(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "active")
    categories = Category.objects.select_related("branch").annotate(product_count=Count("products"))
    if branch:
        categories = categories.filter(branch=branch)
    if q:
        categories = categories.filter(name__icontains=q)
    if status == "active":
        categories = categories.filter(is_active=True)
    elif status == "inactive":
        categories = categories.filter(is_active=False)
    return render(
        request,
        "console/catalog_list.html",
        _page(
            "categories",
            "Categories",
            "Organize canteen and retail items",
            {
                "kind": "categories",
                "categories": categories,
                "q": q,
                "status": status,
                "create_url": reverse("products:category_create"),
            },
        ),
    )


@login_required
def category_create(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    form = CategoryForm(request.POST or None, branch=branch, lock_branch=_lock_branch(request))
    if request.method == "POST" and form.is_valid():
        category = form.save(commit=False)
        if _lock_branch(request):
            category.branch = request.user.branch
        category.save()
        return _saved_response(request, "products:category_list", f"Category “{category.name}” created.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("products:category_list") + "?modal=create")
    return _form_response(
        request,
        form,
        kind="categories",
        title="New category",
        action_url=reverse("products:category_create"),
        list_url=reverse("products:category_list"),
        status=422 if request.method == "POST" else 200,
    )


@login_required
def category_edit(request: HttpRequest, pk: int) -> HttpResponse:
    category = get_object_or_404(Category, pk=pk)
    form = CategoryForm(
        request.POST or None,
        instance=category,
        branch=category.branch,
        lock_branch=_lock_branch(request),
    )
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        if _lock_branch(request):
            saved.branch = request.user.branch
        saved.save()
        return _saved_response(request, "products:category_list", f"Category “{saved.name}” updated.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("products:category_list") + f"?modal=edit&id={pk}")
    return _form_response(
        request,
        form,
        kind="categories",
        title=f"Edit {category.name}",
        action_url=reverse("products:category_edit", args=[pk]),
        list_url=reverse("products:category_list"),
        status=422 if request.method == "POST" else 200,
    )


@login_required
@require_POST
def category_toggle(request: HttpRequest, pk: int) -> HttpResponse:
    category = get_object_or_404(Category, pk=pk)
    category.is_active = not category.is_active
    category.save(update_fields=["is_active", "updated_at"])
    state = "activated" if category.is_active else "deactivated"
    messages.success(request, f"Category “{category.name}” {state}.")
    return redirect("products:category_list")


@login_required
def product_list(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    q = request.GET.get("q", "").strip()
    category_id = request.GET.get("category", "")
    status = request.GET.get("status", "active")
    products = Product.objects.select_related("category", "branch")
    categories = Category.objects.none()
    if branch:
        products = products.filter(branch=branch)
        categories = Category.objects.filter(branch=branch, is_active=True)
    if q:
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(barcode__icontains=q))
    if category_id:
        products = products.filter(category_id=category_id)
    if status == "active":
        products = products.filter(is_active=True)
    elif status == "inactive":
        products = products.filter(is_active=False)
    return render(
        request,
        "console/catalog_list.html",
        _page(
            "products",
            "Products",
            "Catalog, SKUs, and pricing",
            {
                "kind": "products",
                "products": products,
                "categories": categories,
                "q": q,
                "status": status,
                "category_id": category_id,
                "create_url": reverse("products:product_create"),
            },
        ),
    )


@login_required
def product_create(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    form = ProductForm(
        request.POST or None,
        request.FILES or None,
        branch=branch,
        lock_branch=_lock_branch(request),
    )
    if request.method == "POST" and form.is_valid():
        product = form.save(commit=False)
        if _lock_branch(request):
            product.branch = request.user.branch
        product.save()
        return _saved_response(request, "products:product_list", f"Product “{product.name}” created.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("products:product_list") + "?modal=create")
    return _form_response(
        request,
        form,
        kind="products",
        title="New product",
        action_url=reverse("products:product_create"),
        list_url=reverse("products:product_list"),
        status=422 if request.method == "POST" else 200,
    )


@login_required
def product_edit(request: HttpRequest, pk: int) -> HttpResponse:
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(
        request.POST or None,
        request.FILES or None,
        instance=product,
        branch=product.branch,
        lock_branch=_lock_branch(request),
    )
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        if _lock_branch(request):
            saved.branch = request.user.branch
        saved.save()
        return _saved_response(request, "products:product_list", f"Product “{saved.name}” updated.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("products:product_list") + f"?modal=edit&id={pk}")
    return _form_response(
        request,
        form,
        kind="products",
        title=f"Edit {product.name}",
        action_url=reverse("products:product_edit", args=[pk]),
        list_url=reverse("products:product_list"),
        status=422 if request.method == "POST" else 200,
    )


@login_required
@require_POST
def product_toggle(request: HttpRequest, pk: int) -> HttpResponse:
    product = get_object_or_404(Product, pk=pk)
    product.is_active = not product.is_active
    product.save(update_fields=["is_active", "updated_at"])
    state = "activated" if product.is_active else "deactivated"
    messages.success(request, f"Product “{product.name}” {state}.")
    return redirect("products:product_list")
