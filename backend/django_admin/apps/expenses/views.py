from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.branches.models import Branch
from apps.expenses.forms import ExpenseCategoryForm, ExpenseForm
from apps.expenses.models import Expense, ExpenseCategory


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


def _form_response(request, form, *, title: str, action_url: str, list_url: str, status: int = 200):
    context = {
        "form": form,
        "modal_title": title,
        "action_url": action_url,
        "list_url": list_url,
    }
    if _is_partial(request):
        return render(request, "console/partials/catalog_form.html", context, status=status)
    context.update(_page("expenses", title, title))
    context["form_partial"] = "console/partials/catalog_form.html"
    return render(request, "console/catalog_form.html", context, status=status)


def _saved(request, message: str) -> HttpResponse:
    messages.success(request, message)
    if _is_partial(request):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = reverse("expenses:expense_list")
        return response
    return redirect("expenses:expense_list")


@login_required
def expense_list(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    expenses = Expense.objects.select_related("category", "branch", "created_by")
    if branch:
        expenses = expenses.filter(branch=branch)
    return render(
        request,
        "console/expense_list.html",
        _page(
            "expenses",
            "Expenses",
            "Operating expenses and categories",
            {
                "expenses": expenses[:200],
                "create_url": reverse("expenses:expense_create"),
                "category_url": reverse("expenses:category_create"),
            },
        ),
    )


@login_required
def expense_create(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    form = ExpenseForm(request.POST or None, branch=branch, lock_branch=_lock_branch(request))
    if request.method == "POST" and form.is_valid():
        expense = form.save(commit=False)
        if _lock_branch(request):
            expense.branch = request.user.branch
        expense.created_by = request.user
        expense.save()
        from apps.audit.middleware import write_audit_log

        write_audit_log(
            action="expense.create",
            entity_type="expense",
            entity_id=str(expense.id),
            user=request.user,
            new_values={"amount": str(expense.amount), "category": expense.category.name},
        )
        return _saved(request, "Expense recorded.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("expenses:expense_list") + "?modal=create")
    return _form_response(
        request,
        form,
        title="New expense",
        action_url=reverse("expenses:expense_create"),
        list_url=reverse("expenses:expense_list"),
        status=422 if request.method == "POST" else 200,
    )


@login_required
def expense_edit(request: HttpRequest, pk: int) -> HttpResponse:
    expenses = Expense.objects.select_related("branch", "category")
    branch = _working_branch(request)
    if branch:
        expenses = expenses.filter(branch=branch)
    expense = get_object_or_404(expenses, pk=pk)
    form = ExpenseForm(
        request.POST or None,
        instance=expense,
        branch=expense.branch,
        lock_branch=_lock_branch(request),
    )
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        if _lock_branch(request):
            saved.branch = request.user.branch
        saved.save()
        from apps.audit.middleware import write_audit_log

        write_audit_log(
            action="expense.update",
            entity_type="expense",
            entity_id=str(saved.id),
            user=request.user,
            new_values={"amount": str(saved.amount), "category": saved.category.name},
        )
        return _saved(request, "Expense updated.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("expenses:expense_list") + f"?modal=edit&id={pk}")
    return _form_response(
        request,
        form,
        title=f"Edit {expense.category.name} expense",
        action_url=reverse("expenses:expense_edit", args=[pk]),
        list_url=reverse("expenses:expense_list"),
        status=422 if request.method == "POST" else 200,
    )


@login_required
def category_create(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    form = ExpenseCategoryForm(request.POST or None, branch=branch, lock_branch=_lock_branch(request))
    if request.method == "POST" and form.is_valid():
        category = form.save(commit=False)
        if _lock_branch(request):
            category.branch = request.user.branch
        category.save()
        return _saved(request, f"Category “{category.name}” added.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("expenses:expense_list") + "?modal=category")
    return _form_response(
        request,
        form,
        title="New expense category",
        action_url=reverse("expenses:category_create"),
        list_url=reverse("expenses:expense_list"),
        status=422 if request.method == "POST" else 200,
    )
