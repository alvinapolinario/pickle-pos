from django.urls import reverse
import pytest

pytestmark = pytest.mark.django_db


def test_dashboard_requires_login(django_client):
    response = django_client.get("/")
    assert response.status_code == 302
    assert "/login/" in response.url


def test_login_page_renders(django_client):
    response = django_client.get("/login/")
    assert response.status_code == 200
    assert b"Pickleball POS" in response.content
    assert b"Sign in" in response.content


def test_dashboard_renders_after_login(django_client, user):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    response = django_client.get(reverse("console:dashboard"))
    assert response.status_code == 200
    assert b"Total Sales" in response.content
    assert b"Canteen Sales" in response.content
    assert b"Court Revenue" in response.content
    assert b"Transactions" in response.content
    assert b"Gross Profit" in response.content
    assert b"kpi-dashboard" in response.content
    assert b"PICKLEBALL POS" in response.content
    assert b"Recent Transactions" in response.content


def test_users_module_requires_manager(django_client, user):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    response = django_client.get(reverse("accounts:user_list"))
    assert response.status_code == 403


def test_users_console_create_and_edit(django_client, branch):
    from django.contrib.auth import get_user_model

    from apps.accounts.models import Permission, Role
    from core.services.auth_service import AuthService

    User = get_user_model()
    role = Role.objects.create(code="administrator", name="Administrator")
    permission, _ = Permission.objects.get_or_create(
        code="users.manage", defaults={"name": "Manage users", "module": "users"}
    )
    role.permissions.add(permission)
    cashier_role = Role.objects.create(code="cashier", name="Cashier")
    manager = User.objects.create_user(
        username="admin1",
        password="secure-pass-123",
        email="admin1@example.com",
        branch=branch,
    )
    manager.roles.add(role)
    assert django_client.login(username="admin1", password="secure-pass-123")

    listing = django_client.get(reverse("accounts:user_list"))
    assert listing.status_code == 200
    assert b"admin1" in listing.content
    assert b"Add user" in listing.content

    created = django_client.post(
        reverse("accounts:user_create"),
        {
            "username": "pos.cashier",
            "first_name": "Pat",
            "last_name": "Santos",
            "email": "pat@example.com",
            "phone": "09170001111",
            "branch": branch.pk,
            "roles": [cashier_role.pk],
            "password": "secure-pass-123",
            "password_confirm": "secure-pass-123",
            "pin": "2468",
            "pin_confirm": "2468",
            "is_active": "on",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert created.status_code == 204
    cashier = User.objects.get(username="pos.cashier")
    assert cashier.branch_id == branch.pk
    assert list(cashier.roles.values_list("code", flat=True)) == ["cashier"]
    assert cashier.check_password("secure-pass-123")
    assert AuthService().authenticate_user(username="pos.cashier", pin="2468").pk == cashier.pk

    saved = django_client.post(
        reverse("accounts:user_edit", args=[cashier.pk]),
        {
            "username": "pos.cashier",
            "first_name": "Patricia",
            "last_name": "Santos",
            "email": "pat@example.com",
            "phone": "09170001111",
            "branch": branch.pk,
            "roles": [cashier_role.pk],
            "is_active": "on",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert saved.status_code == 204
    cashier.refresh_from_db()
    assert cashier.first_name == "Patricia"
    assert cashier.check_password("secure-pass-123")

    django_client.logout()
    denied = django_client.post("/login/", {"username": "pos.cashier", "password": "secure-pass-123"})
    assert denied.status_code == 200
    assert b"POS tablet" in denied.content
    assert django_client.login(username="admin1", password="secure-pass-123")

    blocked = django_client.post(reverse("accounts:user_toggle", args=[manager.pk]))
    assert blocked.status_code == 302
    manager.refresh_from_db()
    assert manager.is_active is True


def test_pin_only_cashier_cannot_use_console(django_client, branch):
    from django.contrib.auth import get_user_model

    from apps.accounts.models import Permission, Role
    from core.services.auth_service import AuthService

    User = get_user_model()
    admin_role = Role.objects.create(code="administrator", name="Administrator")
    permission, _ = Permission.objects.get_or_create(
        code="users.manage", defaults={"name": "Manage users", "module": "users"}
    )
    admin_role.permissions.add(permission)
    cashier_role = Role.objects.create(code="cashier", name="Cashier")
    admin = User.objects.create_user(
        username="admin1",
        password="secure-pass-123",
        email="admin1@example.com",
        branch=branch,
    )
    admin.roles.add(admin_role)
    assert django_client.login(username="admin1", password="secure-pass-123")

    created = django_client.post(
        reverse("accounts:user_create"),
        {
            "username": "tablet.only",
            "first_name": "Kim",
            "branch": branch.pk,
            "roles": [cashier_role.pk],
            "pin": "1357",
            "pin_confirm": "1357",
            "is_active": "on",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert created.status_code == 204
    cashier = User.objects.get(username="tablet.only")
    assert not cashier.has_usable_password()
    assert AuthService().authenticate_user(username="tablet.only", pin="1357").pk == cashier.pk

    django_client.logout()
    django_client.force_login(cashier)
    blocked = django_client.get(reverse("console:dashboard"))
    assert blocked.status_code == 302
    assert "/login/" in blocked.url


def test_user_edit_is_scoped_to_working_branch(django_client, branch):
    from django.contrib.auth import get_user_model

    from apps.accounts.models import Permission, Role
    from apps.branches.models import Branch

    User = get_user_model()
    other = Branch.objects.create(code="CEB", name="Cebu", city="Cebu")
    admin_role = Role.objects.create(code="administrator", name="Administrator")
    permission, _ = Permission.objects.get_or_create(
        code="users.manage", defaults={"name": "Manage users", "module": "users"}
    )
    admin_role.permissions.add(permission)
    admin = User.objects.create_user(
        username="hq.admin",
        password="secure-pass-123",
        branch=branch,
    )
    admin.roles.add(admin_role)
    outsider = User.objects.create_user(
        username="cebu.staff",
        password="secure-pass-123",
        branch=other,
    )
    outsider.roles.add(admin_role)
    assert django_client.login(username="hq.admin", password="secure-pass-123")
    assert django_client.get(reverse("accounts:user_edit", args=[outsider.pk])).status_code == 404
    assert django_client.post(reverse("accounts:user_toggle", args=[outsider.pk])).status_code == 404


def test_unknown_module_is_404(django_client, user):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    response = django_client.get("/app/not-a-real-page/")
    assert response.status_code == 404


def test_pos_pages_render(django_client, user):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    sales = django_client.get(reverse("sales:sale_list"))
    assert sales.status_code == 200
    assert b"Open a shift before taking sales" in sales.content
    shifts = django_client.get(reverse("shifts:shift_list"))
    assert shifts.status_code == 200
    assert b"Open shift" in shifts.content
    assert django_client.get(reverse("sales:transaction_list")).status_code == 200
    assert django_client.get(reverse("sales:refund_list")).status_code == 200
    assert django_client.get(reverse("courts:court_list")).status_code == 200
    assert django_client.get(reverse("courts:booking_list")).status_code == 200
    assert django_client.get(reverse("courts:court_schedule")).status_code == 200


def test_court_rate_edit(django_client, user, branch):
    from decimal import Decimal

    from apps.courts.models import Court, CourtRate

    court = Court.objects.create(branch=branch, code="C1", name="Court 1", hourly_rate=Decimal("350.00"))
    rate = CourtRate.objects.create(court=court, weekday=5, hourly_rate=Decimal("500.00"))
    assert django_client.login(username="cashier1", password="secure-pass-123")

    listing = django_client.get(reverse("courts:rate_list"))
    assert listing.status_code == 200
    assert b"icon-action-edit" in listing.content

    form_page = django_client.get(
        reverse("courts:rate_edit", args=[rate.pk]),
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert form_page.status_code == 200
    assert b"hourly_rate" in form_page.content

    saved = django_client.post(
        reverse("courts:rate_edit", args=[rate.pk]),
        {
            "court": court.pk,
            "weekday": 6,
            "hourly_rate": "650.00",
            "is_active": "on",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert saved.status_code == 204
    rate.refresh_from_db()
    assert rate.weekday == 6
    assert rate.hourly_rate == Decimal("650.00")


def test_expense_edit(django_client, user, branch):
    from datetime import date
    from decimal import Decimal

    from apps.expenses.models import Expense, ExpenseCategory

    category = ExpenseCategory.objects.create(branch=branch, name="Utilities")
    expense = Expense.objects.create(
        branch=branch,
        category=category,
        amount=Decimal("100.00"),
        incurred_on=date(2026, 8, 1),
        notes="Electric",
        created_by=user,
    )
    assert django_client.login(username="cashier1", password="secure-pass-123")

    listing = django_client.get(reverse("expenses:expense_list"))
    assert listing.status_code == 200
    assert b"icon-action-edit" in listing.content

    saved = django_client.post(
        reverse("expenses:expense_edit", args=[expense.pk]),
        {
            "branch": branch.pk,
            "category": category.pk,
            "amount": "150.00",
            "incurred_on": "2026-08-02",
            "notes": "Electric + water",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert saved.status_code == 204
    expense.refresh_from_db()
    assert expense.amount == Decimal("150.00")
    assert expense.notes == "Electric + water"


def test_membership_tier_and_member_edit(django_client, user, branch):
    from datetime import date
    from decimal import Decimal

    from apps.customers.models import Customer
    from apps.membership.models import Membership, MembershipTier

    tier = MembershipTier.objects.create(
        branch=branch,
        code="PREMIUM",
        name="Premium",
        court_discount_pct=Decimal("10.00"),
        canteen_discount_pct=Decimal("5.00"),
    )
    customer = Customer.objects.create(branch=branch, name="Ana Cruz", mobile="09170000000")
    membership = Membership.objects.create(
        branch=branch,
        customer=customer,
        tier=tier,
        started_on=date(2026, 8, 1),
        expires_on=date(2026, 12, 31),
    )
    assert django_client.login(username="cashier1", password="secure-pass-123")

    listing = django_client.get(reverse("membership:membership_list"))
    assert listing.status_code == 200
    assert listing.content.count(b"icon-action-edit") >= 2

    saved_tier = django_client.post(
        reverse("membership:tier_edit", args=[tier.pk]),
        {
            "branch": branch.pk,
            "code": "PREMIUM",
            "name": "Premium Plus",
            "court_discount_pct": "15.00",
            "canteen_discount_pct": "8.00",
            "points_per_peso": "0.1000",
            "sort_order": "10",
            "is_active": "on",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert saved_tier.status_code == 204
    tier.refresh_from_db()
    assert tier.name == "Premium Plus"
    assert tier.court_discount_pct == Decimal("15.00")

    saved_member = django_client.post(
        reverse("membership:membership_edit", args=[membership.pk]),
        {
            "branch": branch.pk,
            "customer": customer.pk,
            "tier": tier.pk,
            "started_on": "2026-08-01",
            "expires_on": "2027-01-31",
            "notes": "Extended",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert saved_member.status_code == 204
    membership.refresh_from_db()
    assert membership.expires_on == date(2027, 1, 31)
    assert membership.notes == "Extended"


def test_membership_edit_cancels_other_active(django_client, user, branch):
    from datetime import date
    from decimal import Decimal

    from apps.customers.models import Customer
    from apps.membership.models import Membership, MembershipTier

    tier = MembershipTier.objects.create(
        branch=branch,
        code="PREMIUM",
        name="Premium",
        court_discount_pct=Decimal("10.00"),
        canteen_discount_pct=Decimal("5.00"),
    )
    first = Customer.objects.create(branch=branch, name="Ana Cruz", mobile="09170000001")
    second = Customer.objects.create(branch=branch, name="Ben Cruz", mobile="09170000002")
    existing = Membership.objects.create(
        branch=branch,
        customer=second,
        tier=tier,
        started_on=date(2026, 1, 1),
        status=Membership.Status.ACTIVE,
    )
    moving = Membership.objects.create(
        branch=branch,
        customer=first,
        tier=tier,
        started_on=date(2026, 8, 1),
        status=Membership.Status.ACTIVE,
    )
    assert django_client.login(username="cashier1", password="secure-pass-123")
    saved = django_client.post(
        reverse("membership:membership_edit", args=[moving.pk]),
        {
            "branch": branch.pk,
            "customer": second.pk,
            "tier": tier.pk,
            "started_on": "2026-08-01",
            "notes": "Moved",
        },
        HTTP_X_REQUESTED_WITH="XMLHttpRequest",
    )
    assert saved.status_code == 204
    existing.refresh_from_db()
    moving.refresh_from_db()
    assert existing.status == Membership.Status.CANCELLED
    assert moving.status == Membership.Status.ACTIVE
    assert moving.customer_id == second.pk
