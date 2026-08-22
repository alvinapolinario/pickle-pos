import csv
from datetime import date

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.accounts.models import Role, User
from apps.audit.middleware import write_audit_log
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.console.dashboard_data import dashboard_data
from apps.console.navigation import PAGE_META, page_meta
from core.domain.auth import user_has_permission
from core.domain.exceptions import AuthenticationError
from core.services.auth_service import AuthService
from core.services.report_pdf import ReportPdfService
from core.services.report_service import ReportService


def _console_auth_service() -> AuthService:
    return AuthService()


def _staff_permissions(user) -> frozenset[str]:
    permissions: set[str] = set()
    for role in user.roles.prefetch_related("permissions").all():
        permissions.update(role.permissions.values_list("code", flat=True))
    return frozenset(permissions)


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("console:dashboard")

    form = AuthenticationForm(request, data=request.POST or None)
    form.fields["username"].widget.attrs.update(
        {"placeholder": "Username", "autofocus": True, "class": "field-input"}
    )
    form.fields["password"].widget.attrs.update(
        {"placeholder": "Password", "class": "field-input"}
    )
    auth_service = _console_auth_service()
    username = (request.POST.get("username") or "").strip()
    if request.method == "POST" and username:
        try:
            auth_service.lockout.assert_unlocked(username)
        except AuthenticationError as exc:
            form.add_error(None, exc.message)
            return render(
                request,
                "console/login.html",
                {"form": form, "next": request.GET.get("next", "")},
            )

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        auth_service.lockout.clear(username)
        login(request, user)
        write_audit_log(action="auth.login", entity_type="user", entity_id=str(user.id), user=user)
        next_url = request.POST.get("next") or request.GET.get("next") or "/"
        if not url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = "/"
        return redirect(next_url)

    if request.method == "POST" and username and not form.is_valid():
        try:
            auth_service.lockout.record_failure(username)
        except AuthenticationError as exc:
            form.add_error(None, exc.message)

    return render(
        request,
        "console/login.html",
        {"form": form, "next": request.GET.get("next", "")},
    )


@require_POST
@login_required
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("console:login")


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    branch = request.user.branch if getattr(request.user, "branch_id", None) else None
    data = dashboard_data(branch)
    return render(
        request,
        "console/dashboard.html",
        {
            "page_name": "dashboard",
            "page_title": "Dashboard",
            "page_subtitle": "Overview of your business",
            "report_date": date.today(),
            **data,
        },
    )


@login_required
def module_page(request: HttpRequest, page_name: str) -> HttpResponse:
    if page_name not in PAGE_META or page_name == "dashboard":
        raise Http404()

    meta = page_meta(page_name)
    context = {
        "page_name": page_name,
        "page_title": meta["title"],
        "page_subtitle": meta["subtitle"],
        "report_date": date.today(),
        "rows": [],
        "empty_message": f"{meta['title']} will be available when this module is implemented.",
    }

    if page_name == "users":
        context["columns"] = ["Username", "Name", "Branch", "Role", "Status"]
        context["rows"] = [
            [
                user.username,
                user.get_full_name() or "—",
                user.branch.name if user.branch else "—",
                ", ".join(user.roles.values_list("name", flat=True)) or "—",
                "Active" if user.is_active else "Inactive",
            ]
            for user in User.objects.select_related("branch").prefetch_related("roles").order_by("username")
        ]
        context["empty_message"] = "No users found."
    elif page_name == "roles":
        context["columns"] = ["Role", "Code", "Permissions", "Status"]
        context["rows"] = [
            [
                role.name,
                role.code,
                str(role.permissions.count()),
                "Active" if role.is_active else "Inactive",
            ]
            for role in Role.objects.prefetch_related("permissions").order_by("name")
        ]
        context["empty_message"] = "No roles found. Run seed_rbac first."
    elif page_name == "settings":
        if request.method == "POST":
            for branch in Branch.objects.all():
                branch.vat_registered = request.POST.get(f"vat_{branch.id}") == "1"
                branch.memberships_enabled = request.POST.get(f"memberships_{branch.id}") == "1"
                branch.save(update_fields=["vat_registered", "memberships_enabled", "updated_at"])
            return redirect("console:module", page_name="settings")
        context["branches"] = Branch.objects.order_by("name")
        return render(request, "console/settings.html", context)

    return render(request, "console/module.html", context)


def _report_range(request: HttpRequest) -> tuple[date, date]:
    today = date.today()
    raw_start = request.GET.get("from") or today.replace(day=1).isoformat()
    raw_end = request.GET.get("to") or today.isoformat()
    try:
        start = date.fromisoformat(raw_start)
        end = date.fromisoformat(raw_end)
    except ValueError:
        start, end = today.replace(day=1), today
    if start > end:
        start, end = end, start
    return start, end


def _csv_response(filename: str, headers: list[str], rows: list[list]) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    writer.writerows(rows)
    return response


def _pdf_response(filename: str, content: bytes) -> HttpResponse:
    response = HttpResponse(content, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _branch_label(request: HttpRequest) -> str:
    branch = request.user.branch if getattr(request.user, "branch_id", None) else None
    return branch.name if branch else "All branches"


@login_required
def report_sales(request: HttpRequest) -> HttpResponse:
    start, end = _report_range(request)
    branch = request.user.branch if getattr(request.user, "branch_id", None) else None
    report = ReportService().sales_report(branch_id=branch.id if branch else None, start=start, end=end)
    if request.GET.get("export") == "csv":
        return _csv_response(
            f"sales-{start.isoformat()}-{end.isoformat()}.csv",
            ["Day", "Tickets", "Net"],
            [[row["day"], row["count"], row["total"]] for row in report["days"]],
        )
    if request.GET.get("export") == "pdf":
        return _pdf_response(
            f"sales-{start.isoformat()}-{end.isoformat()}.pdf",
            ReportPdfService().sales(report, branch_name=_branch_label(request)),
        )
    meta = page_meta("report_sales")
    return render(
        request,
        "console/report_sales.html",
        {
            "page_name": "report_sales",
            "page_title": meta["title"],
            "page_subtitle": meta["subtitle"],
            "report_date": date.today(),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "report": report,
        },
    )


@login_required
def report_courts(request: HttpRequest) -> HttpResponse:
    start, end = _report_range(request)
    branch = request.user.branch if getattr(request.user, "branch_id", None) else None
    report = ReportService().court_report(branch_id=branch.id if branch else None, start=start, end=end)
    if request.GET.get("export") == "csv":
        return _csv_response(
            f"courts-{start.isoformat()}-{end.isoformat()}.csv",
            ["Court", "Bookings", "Cancelled", "Hours", "Revenue"],
            [[row["name"], row["bookings"], row["cancelled"], row["hours"], row["revenue"]] for row in report["courts"]],
        )
    if request.GET.get("export") == "pdf":
        return _pdf_response(
            f"courts-{start.isoformat()}-{end.isoformat()}.pdf",
            ReportPdfService().courts(report, branch_name=_branch_label(request)),
        )
    meta = page_meta("report_courts")
    return render(
        request,
        "console/report_courts.html",
        {
            "page_name": "report_courts",
            "page_title": meta["title"],
            "page_subtitle": meta["subtitle"],
            "report_date": date.today(),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "report": report,
        },
    )


@login_required
def report_inventory(request: HttpRequest) -> HttpResponse:
    start, end = _report_range(request)
    branch = request.user.branch if getattr(request.user, "branch_id", None) else None
    report = ReportService().inventory_report(branch_id=branch.id if branch else None, start=start, end=end)
    if request.GET.get("export") == "csv":
        return _csv_response(
            f"inventory-{start.isoformat()}-{end.isoformat()}.csv",
            ["SKU", "Product", "On hand", "Cost", "Value", "Low"],
            [
                [row["sku"], row["name"], row["qty"], row["cost"], row["value"], "yes" if row["is_low"] else ""]
                for row in report["stock"]
            ],
        )
    if request.GET.get("export") == "pdf":
        return _pdf_response(
            f"inventory-{start.isoformat()}-{end.isoformat()}.pdf",
            ReportPdfService().inventory(report, branch_name=_branch_label(request)),
        )
    meta = page_meta("report_inventory")
    return render(
        request,
        "console/report_inventory.html",
        {
            "page_name": "report_inventory",
            "page_title": meta["title"],
            "page_subtitle": meta["subtitle"],
            "report_date": date.today(),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "report": report,
        },
    )


@login_required
def report_financial(request: HttpRequest) -> HttpResponse:
    start, end = _report_range(request)
    branch = request.user.branch if getattr(request.user, "branch_id", None) else None
    report = ReportService().financial_report(branch_id=branch.id if branch else None, start=start, end=end)
    if request.GET.get("export") == "csv":
        return _csv_response(
            f"financial-{start.isoformat()}-{end.isoformat()}.csv",
            ["Line", "Amount"],
            [[row["label"], row["amount"]] for row in report["lines"]],
        )
    if request.GET.get("export") == "pdf":
        return _pdf_response(
            f"financial-{start.isoformat()}-{end.isoformat()}.pdf",
            ReportPdfService().financial(report, branch_name=_branch_label(request)),
        )
    meta = page_meta("report_financial")
    return render(
        request,
        "console/report_financial.html",
        {
            "page_name": "report_financial",
            "page_title": meta["title"],
            "page_subtitle": meta["subtitle"],
            "report_date": date.today(),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "report": report,
        },
    )


@login_required
def audit_list(request: HttpRequest) -> HttpResponse:
    if not request.user.is_superuser and not user_has_permission(
        _staff_permissions(request.user), "audit.view"
    ):
        raise PermissionDenied
    logs = AuditLog.objects.select_related("user")
    action = (request.GET.get("action") or "").strip()
    entity_type = (request.GET.get("entity") or "").strip()
    username = (request.GET.get("user") or "").strip()
    if action:
        logs = logs.filter(action__icontains=action)
    if entity_type:
        logs = logs.filter(entity_type__icontains=entity_type)
    if username:
        logs = logs.filter(user__username__icontains=username)
    meta = page_meta("audit")
    return render(
        request,
        "console/audit_list.html",
        {
            "page_name": "audit",
            "page_title": meta["title"],
            "page_subtitle": meta["subtitle"],
            "report_date": date.today(),
            "logs": logs[:300],
            "filter_action": action,
            "filter_entity": entity_type,
            "filter_user": username,
        },
    )
