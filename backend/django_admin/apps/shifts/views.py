from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.branches.models import Branch
from apps.sales.forms import CashMoveForm, ShiftCloseForm, ShiftOpenForm
from apps.shifts.models import CashierShift
from core.domain.exceptions import DomainError
from core.domain.shifts import CASH_IN, CASH_OUT, OPEN
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


def _form_response(request, template: str, context: dict, status: int = 200) -> HttpResponse:
    if _is_partial(request):
        return render(request, template, context, status=status)
    context["form_partial"] = template
    context.update(_page("shifts", context.get("modal_title", ""), "Shifts"))
    return render(request, "console/catalog_form.html", context, status=status)


def _saved(request, message: str) -> HttpResponse:
    messages.success(request, message)
    if _is_partial(request):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = reverse("shifts:shift_list")
        return response
    return redirect("shifts:shift_list")


@login_required
def shift_list(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    current = ShiftService().current_shift(cashier_id=request.user.id, branch_id=branch.id if branch else None)
    shifts = CashierShift.objects.select_related("cashier", "branch")
    if branch:
        shifts = shifts.filter(branch=branch)
    return render(
        request,
        "console/shift_list.html",
        _page(
            "shifts",
            "Shift Management",
            "Open, close, and reconcile cashier shifts",
            {
                "shifts": shifts[:100],
                "current_shift": current,
                "expected_cash": ShiftService().expected_cash(current) if current else None,
                "open_url": reverse("shifts:shift_open"),
                "close_url": reverse("shifts:shift_close", args=[current.pk]) if current else "",
                "cash_in_url": reverse("shifts:shift_cash_in", args=[current.pk]) if current else "",
                "cash_out_url": reverse("shifts:shift_cash_out", args=[current.pk]) if current else "",
            },
        ),
    )


@login_required
def shift_open(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    form = ShiftOpenForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            if branch is None:
                raise DomainError("No branch available.")
            shift = ShiftService().open_shift(
                cashier_id=request.user.id,
                branch_id=branch.id,
                opening_cash=form.cleaned_data["opening_cash"],
                notes=form.cleaned_data.get("notes") or "",
            )
        except DomainError as exc:
            form.add_error(None, exc.message)
        else:
            return _saved(request, f"Shift opened with ₱ {shift.opening_cash} opening cash.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("shifts:shift_list") + "?modal=create")
    return _form_response(
        request,
        "console/partials/catalog_form.html",
        {
            "form": form,
            "modal_title": "Open shift",
            "action_url": reverse("shifts:shift_open"),
            "list_url": reverse("shifts:shift_list"),
            "submit_label": "Open shift",
        },
        status=422 if request.method == "POST" else 200,
    )


def _cash_move(request: HttpRequest, pk: int, transaction_type: str, title: str) -> HttpResponse:
    form = CashMoveForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            ShiftService().add_cash(
                shift_id=pk,
                amount=form.cleaned_data["amount"],
                reason=form.cleaned_data.get("reason") or "",
                performed_by_id=request.user.id,
                transaction_type=transaction_type,
            )
        except DomainError as exc:
            form.add_error(None, exc.message)
        else:
            return _saved(request, f"{title} posted.")
    name = "cash-in" if transaction_type == CASH_IN else "cash-out"
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("shifts:shift_list") + f"?modal={name}&id={pk}")
    action = reverse("shifts:shift_cash_in" if transaction_type == CASH_IN else "shifts:shift_cash_out", args=[pk])
    return _form_response(
        request,
        "console/partials/catalog_form.html",
        {
            "form": form,
            "modal_title": title,
            "action_url": action,
            "list_url": reverse("shifts:shift_list"),
            "submit_label": "Post",
        },
        status=422 if request.method == "POST" else 200,
    )


@login_required
def shift_cash_in(request: HttpRequest, pk: int) -> HttpResponse:
    return _cash_move(request, pk, CASH_IN, "Cash in")


@login_required
def shift_cash_out(request: HttpRequest, pk: int) -> HttpResponse:
    return _cash_move(request, pk, CASH_OUT, "Cash out")


@login_required
def shift_close(request: HttpRequest, pk: int) -> HttpResponse:
    shift = get_object_or_404(CashierShift, pk=pk)
    form = ShiftCloseForm(request.POST or None, initial={"actual_cash": ShiftService().expected_cash(shift)})
    if request.method == "POST" and form.is_valid():
        try:
            closed = ShiftService().close_shift(
                shift_id=pk,
                actual_cash=form.cleaned_data["actual_cash"],
                notes=form.cleaned_data.get("notes") or "",
            )
        except DomainError as exc:
            form.add_error(None, exc.message)
        else:
            over = closed.over_short
            return _saved(request, f"Shift closed. Over/short ₱ {over}.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("shifts:shift_list") + f"?modal=close&id={pk}")
    return _form_response(
        request,
        "console/partials/catalog_form.html",
        {
            "form": form,
            "modal_title": "Close shift",
            "action_url": reverse("shifts:shift_close", args=[pk]),
            "list_url": reverse("shifts:shift_list"),
            "submit_label": "Close shift",
        },
        status=422 if request.method == "POST" else 200,
    )


@login_required
def shift_detail(request: HttpRequest, pk: int) -> HttpResponse:
    shift = get_object_or_404(CashierShift.objects.select_related("cashier", "branch"), pk=pk)
    txns = shift.cash_transactions.select_related("performed_by")
    context = {
        "shift": shift,
        "transactions": txns,
        "expected_cash": shift.expected_cash if shift.status != OPEN else ShiftService().expected_cash(shift),
        "modal_title": f"Shift #{shift.pk}",
    }
    if _is_partial(request) or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(request, "console/partials/shift_detail.html", context)
    return redirect("shifts:shift_list")
