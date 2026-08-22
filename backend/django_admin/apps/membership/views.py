from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.branches.models import Branch
from apps.membership.forms import MembershipForm, MembershipTierForm
from apps.membership.models import Membership, MembershipTier
from core.services.membership_service import MembershipService


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


def _form_response(request, form, *, title: str, action_url: str, status: int = 200):
    context = {
        "form": form,
        "modal_title": title,
        "action_url": action_url,
        "list_url": reverse("membership:membership_list"),
    }
    if _is_partial(request):
        return render(request, "console/partials/catalog_form.html", context, status=status)
    context.update(_page("memberships", title, title))
    context["form_partial"] = "console/partials/catalog_form.html"
    return render(request, "console/catalog_form.html", context, status=status)


def _saved(request, message: str) -> HttpResponse:
    messages.success(request, message)
    if _is_partial(request):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = reverse("membership:membership_list")
        return response
    return redirect("membership:membership_list")


@login_required
def membership_list(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    tiers = MembershipTier.objects.select_related("branch")
    members = Membership.objects.select_related("customer", "tier", "branch")
    if branch:
        tiers = tiers.filter(branch=branch)
        members = members.filter(branch=branch)
    return render(
        request,
        "console/membership_list.html",
        _page(
            "memberships",
            "Memberships",
            "Tiers, benefits, and active members",
            {
                "tiers": tiers,
                "memberships": members[:200],
                "memberships_enabled": bool(branch.memberships_enabled) if branch else True,
                "tier_url": reverse("membership:tier_create"),
                "assign_url": reverse("membership:membership_assign"),
            },
        ),
    )


@login_required
def tier_create(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    form = MembershipTierForm(request.POST or None, branch=branch, lock_branch=_lock_branch(request))
    if request.method == "POST" and form.is_valid():
        tier = form.save(commit=False)
        if _lock_branch(request):
            tier.branch = request.user.branch
        tier.save()
        return _saved(request, f"Tier “{tier.name}” saved.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("membership:membership_list") + "?modal=tier")
    return _form_response(
        request,
        form,
        title="New membership tier",
        action_url=reverse("membership:tier_create"),
        status=422 if request.method == "POST" else 200,
    )


@login_required
def membership_assign(request: HttpRequest) -> HttpResponse:
    branch = _working_branch(request)
    form = MembershipForm(request.POST or None, branch=branch, lock_branch=_lock_branch(request))
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        assigned_branch = request.user.branch if _lock_branch(request) else data["branch"]
        MembershipService().assign(
            branch_id=assigned_branch.id,
            customer_id=data["customer"].id,
            tier_id=data["tier"].id,
            started_on=data["started_on"],
            expires_on=data["expires_on"],
            notes=data["notes"],
        )
        return _saved(request, f"Membership assigned to {data['customer']}.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("membership:membership_list") + "?modal=assign")
    return _form_response(
        request,
        form,
        title="Assign membership",
        action_url=reverse("membership:membership_assign"),
        status=422 if request.method == "POST" else 200,
    )


@login_required
@require_POST
def membership_cancel(request: HttpRequest, pk: int) -> HttpResponse:
    membership = get_object_or_404(Membership, pk=pk)
    membership.status = Membership.Status.CANCELLED
    membership.save(update_fields=["status", "updated_at"])
    messages.success(request, f"Membership for {membership.customer} cancelled.")
    return redirect("membership:membership_list")
