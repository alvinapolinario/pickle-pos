from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.branches.models import Branch
from apps.customers.forms import CustomerForm
from apps.customers.models import Customer
from apps.sales.models import Sale


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


def _lock_branch(request: HttpRequest) -> bool:
    return bool(request.user.branch_id)


def _is_partial(request: HttpRequest) -> bool:
    return request.GET.get("partial") == "1" or request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _form_response(request, form, *, title: str, action_url: str, status: int = 200) -> HttpResponse:
    context = {
        "form": form,
        "modal_title": title,
        "action_url": action_url,
        "list_url": reverse("customers:customer_list"),
    }
    if _is_partial(request):
        return render(request, "console/partials/catalog_form.html", context, status=status)
    context.update(_page("customers", title, "Customers"))
    context["form_partial"] = "console/partials/catalog_form.html"
    return render(request, "console/catalog_form.html", context, status=status)


def _saved(request, message: str) -> HttpResponse:
    messages.success(request, message)
    if _is_partial(request):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = reverse("customers:customer_list")
        return response
    return redirect("customers:customer_list")


@login_required
def customer_list(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "active")
    customers = Customer.objects.select_related("branch").annotate(sale_count=Count("sales"))
    if branch:
        customers = customers.filter(branch=branch)
    if q:
        customers = customers.filter(Q(name__icontains=q) | Q(mobile__icontains=q) | Q(email__icontains=q))
    if status == "active":
        customers = customers.filter(is_active=True)
    elif status == "inactive":
        customers = customers.filter(is_active=False)
    return render(
        request,
        "console/customer_list.html",
        _page(
            "customers",
            "Customers",
            "Customer profiles and history",
            {
                "customers": customers[:200],
                "q": q,
                "status": status,
                "create_url": reverse("customers:customer_create"),
            },
        ),
    )


@login_required
def customer_create(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    form = CustomerForm(request.POST or None, branch=branch, lock_branch=_lock_branch(request))
    if request.method == "POST" and form.is_valid():
        customer = form.save(commit=False)
        if _lock_branch(request):
            customer.branch = request.user.branch
        customer.save()
        return _saved(request, f"Customer “{customer.name}” created.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("customers:customer_list") + "?modal=create")
    return _form_response(
        request,
        form,
        title="New customer",
        action_url=reverse("customers:customer_create"),
        status=422 if request.method == "POST" else 200,
    )


@login_required
def customer_edit(request: HttpRequest, pk: int) -> HttpResponse:
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(
        request.POST or None,
        instance=customer,
        branch=customer.branch,
        lock_branch=_lock_branch(request),
    )
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        if _lock_branch(request):
            saved.branch = request.user.branch
        saved.save()
        return _saved(request, f"Customer “{saved.name}” updated.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("customers:customer_list") + f"?modal=edit&id={pk}")
    return _form_response(
        request,
        form,
        title=f"Edit {customer.name}",
        action_url=reverse("customers:customer_edit", args=[pk]),
        status=422 if request.method == "POST" else 200,
    )


@login_required
@require_POST
def customer_toggle(request: HttpRequest, pk: int) -> HttpResponse:
    customer = get_object_or_404(Customer, pk=pk)
    customer.is_active = not customer.is_active
    customer.save(update_fields=["is_active", "updated_at"])
    state = "activated" if customer.is_active else "deactivated"
    messages.success(request, f"Customer “{customer.name}” {state}.")
    return redirect("customers:customer_list")


@login_required
def customer_detail(request: HttpRequest, pk: int) -> HttpResponse:
    customer = get_object_or_404(Customer, pk=pk)
    sales = Sale.objects.filter(customer=customer).order_by("-created_at")[:40]
    context = {"customer": customer, "sales": sales, "modal_title": customer.name}
    if _is_partial(request) or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(request, "console/partials/customer_detail.html", context)
    return redirect("customers:customer_list")
