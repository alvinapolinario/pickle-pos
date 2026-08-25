from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.accounts.forms import StaffUserForm
from apps.accounts.models import Role, User
from apps.audit.middleware import write_audit_log
from apps.branches.models import Branch
from core.domain.auth import user_has_permission


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


def _can_manage_users(user) -> bool:
    return bool(user.is_superuser or user_has_permission(frozenset(user.permission_codes), "users.manage"))


def _require_manager(request: HttpRequest) -> None:
    if not _can_manage_users(request.user):
        raise PermissionDenied


def _managed_users(request: HttpRequest):
    users = User.objects.select_related("branch").prefetch_related("roles")
    if request.user.branch_id:
        users = users.filter(Q(branch_id=request.user.branch_id) | Q(branch__isnull=True))
    return users


def _form_response(request, form, *, title: str, action_url: str, list_url: str, page_name: str, status: int = 200):
    context = {
        "form": form,
        "modal_title": title,
        "action_url": action_url,
        "list_url": list_url,
    }
    if _is_partial(request):
        return render(request, "console/partials/catalog_form.html", context, status=status)
    context.update(_page(page_name, title, title))
    context["form_partial"] = "console/partials/catalog_form.html"
    return render(request, "console/catalog_form.html", context, status=status)


def _saved(request, list_url: str, message: str) -> HttpResponse:
    messages.success(request, message)
    if _is_partial(request):
        response = HttpResponse(status=204)
        response["HX-Redirect"] = list_url
        return response
    return redirect(list_url)


def _list_url(default_role: str = "") -> str:
    if default_role == "cashier":
        return reverse("accounts:cashier_list")
    return reverse("accounts:user_list")


@login_required
def user_list(request: HttpRequest, default_role: str = "") -> HttpResponse:
    _require_manager(request)
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "active")
    role_code = request.GET.get("role") or default_role
    users = _managed_users(request).order_by("username")
    if q:
        users = users.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(email__icontains=q)
        )
    if status == "active":
        users = users.filter(is_active=True)
    elif status == "inactive":
        users = users.filter(is_active=False)
    if role_code:
        users = users.filter(roles__code=role_code)
    cashiers_only = default_role == "cashier"
    return render(
        request,
        "console/user_list.html",
        _page(
            "cashiers" if cashiers_only else "users",
            "Cashiers" if cashiers_only else "Users",
            "Cashier profiles and PIN access" if cashiers_only else "Staff accounts and branch assignment",
            {
                "users": users.distinct()[:200],
                "q": q,
                "status": status,
                "role": role_code,
                "roles": Role.objects.filter(is_active=True),
                "cashiers_only": cashiers_only,
                "create_url": reverse("accounts:user_create"),
            },
        ),
    )


@login_required
def user_create(request: HttpRequest) -> HttpResponse:
    _require_manager(request)
    branch = _working_branch(request)
    list_url = _list_url(request.GET.get("from", ""))
    form = StaffUserForm(request.POST or None, branch=branch, lock_branch=_lock_branch(request))
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        if _lock_branch(request):
            saved.branch = request.user.branch
        saved.save()
        form.save_m2m()
        write_audit_log(
            action="user.create",
            entity_type="user",
            entity_id=str(saved.id),
            user=request.user,
            new_values={"username": saved.username, "roles": list(saved.roles.values_list("code", flat=True))},
        )
        return _saved(request, list_url, f"User “{saved.username}” created.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("accounts:user_list") + "?modal=create")
    return _form_response(
        request,
        form,
        title="New user",
        action_url=reverse("accounts:user_create"),
        list_url=list_url,
        page_name="users",
        status=422 if request.method == "POST" else 200,
    )


@login_required
def user_edit(request: HttpRequest, pk: int) -> HttpResponse:
    _require_manager(request)
    staff = get_object_or_404(_managed_users(request), pk=pk)
    form = StaffUserForm(
        request.POST or None,
        instance=staff,
        branch=staff.branch or _working_branch(request),
        lock_branch=_lock_branch(request),
    )
    if request.method == "POST" and form.is_valid():
        if staff.pk == request.user.pk and not form.cleaned_data.get("is_active"):
            form.add_error("is_active", "You cannot deactivate your own account.")
        else:
            saved = form.save(commit=False)
            if _lock_branch(request):
                saved.branch = request.user.branch
            saved.save()
            form.save_m2m()
            write_audit_log(
                action="user.update",
                entity_type="user",
                entity_id=str(saved.id),
                user=request.user,
                new_values={"username": saved.username, "roles": list(saved.roles.values_list("code", flat=True))},
            )
            return _saved(request, reverse("accounts:user_list"), f"User “{saved.username}” updated.")
    if request.method == "GET" and not _is_partial(request):
        return redirect(reverse("accounts:user_list") + f"?modal=edit&id={pk}")
    return _form_response(
        request,
        form,
        title=f"Edit {staff.username}",
        action_url=reverse("accounts:user_edit", args=[pk]),
        list_url=reverse("accounts:user_list"),
        page_name="users",
        status=422 if request.method == "POST" else 200,
    )


@login_required
@require_POST
def user_toggle(request: HttpRequest, pk: int) -> HttpResponse:
    _require_manager(request)
    staff = get_object_or_404(_managed_users(request), pk=pk)
    if staff.pk == request.user.pk:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("accounts:user_list")
    staff.is_active = not staff.is_active
    staff.save(update_fields=["is_active", "updated_at"])
    state = "activated" if staff.is_active else "deactivated"
    write_audit_log(
        action="user.activate" if staff.is_active else "user.deactivate",
        entity_type="user",
        entity_id=str(staff.id),
        user=request.user,
        new_values={"username": staff.username, "is_active": staff.is_active},
    )
    messages.success(request, f"User “{staff.username}” {state}.")
    return redirect("accounts:user_list")
