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
    assert b"PICKLEBALL POS" in response.content
    assert b"Recent Transactions" in response.content


def test_users_module_lists_staff(django_client, user):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    response = django_client.get(reverse("console:module", args=["users"]))
    assert response.status_code == 200
    assert b"cashier1" in response.content


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
