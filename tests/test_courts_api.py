from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.courts.models import Court


@pytest.fixture
def court(branch):
    return Court.objects.create(branch=branch, code="C1", name="Court 1", hourly_rate=Decimal("350.00"))


def _auth_headers(api_client):
    login = api_client.post("/api/v1/auth/login", json={"username": "cashier1", "password": "secure-pass-123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _slot():
    start = (timezone.localtime() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    return start, start + timedelta(hours=1)


@pytest.mark.django_db(transaction=True)
def test_list_quote_book_and_reject_overlap(api_client, user, court):
    headers = _auth_headers(api_client)
    courts = api_client.get("/api/v1/courts", headers=headers)
    assert courts.status_code == 200
    assert courts.json()[0]["name"] == "Court 1"

    start, end = _slot()
    payload = {"court_id": court.id, "start_at": start.isoformat(), "end_at": end.isoformat()}
    quoted = api_client.post("/api/v1/bookings/quote", json=payload, headers=headers)
    assert quoted.status_code == 200
    assert quoted.json()["amount"] in ("350.00", "350.0", 350)

    created = api_client.post("/api/v1/bookings", json={**payload, "payment_method": "gcash"}, headers=headers)
    assert created.status_code == 200
    assert created.json()["status"] == "confirmed"

    conflict = api_client.post("/api/v1/bookings", json=payload, headers=headers)
    assert conflict.status_code == 409

    listed = api_client.get("/api/v1/bookings", params={"date": start.date().isoformat()}, headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    cancelled = api_client.post(f"/api/v1/bookings/{created.json()['id']}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    rebooked = api_client.post("/api/v1/bookings", json={**payload, "payment_method": "cash"}, headers=headers)
    assert rebooked.status_code == 200
    refunded = api_client.post(
        f"/api/v1/bookings/{rebooked.json()['id']}/refund",
        json={"method": "cash", "reason": "Customer cancelled"},
        headers=headers,
    )
    assert refunded.status_code == 200
    assert refunded.json()["payment_status"] == "refunded"
    assert refunded.json()["status"] == "cancelled"
