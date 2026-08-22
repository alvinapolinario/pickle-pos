import pytest

from apps.accounts.models import PosConnection
from core.services.pairing_service import (
    PairingService,
    encode_payload,
    parse_payload,
    qr_png_bytes,
)


def test_payload_round_trip():
    payload = encode_payload("http://10.0.0.12:7101/", "abc-key")
    assert payload.startswith("picklepos://connect?")
    assert parse_payload(payload) == ("http://10.0.0.12:7101", "abc-key")
    assert parse_payload('{"v":1,"url":"http://10.0.0.12:7101/","key":"abc-key"}') == (
        "http://10.0.0.12:7101",
        "abc-key",
    )
    assert parse_payload("not-a-code") is None


def test_qr_png_is_a_png():
    png = qr_png_bytes(encode_payload("http://127.0.0.1:7101", "secret"))
    assert png.startswith(b"\x89PNG")


@pytest.mark.django_db
def test_pairing_creates_and_regenerates_key():
    first = PairingService().get_or_create()
    assert first.api_key
    assert first.public_base_url
    second = PairingService().regenerate()
    assert second.api_key != first.api_key
    assert PosConnection.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_api_requires_pairing_key_once_created(api_client, user):
    open_login = api_client.post(
        "/api/v1/auth/login",
        json={"username": "cashier1", "password": "secure-pass-123"},
    )
    assert open_login.status_code == 200

    info = PairingService().get_or_create()
    blocked = api_client.post(
        "/api/v1/auth/login",
        json={"username": "cashier1", "password": "secure-pass-123"},
    )
    assert blocked.status_code == 401

    allowed = api_client.post(
        "/api/v1/auth/login",
        headers={"X-Api-Key": info.api_key},
        json={"username": "cashier1", "password": "secure-pass-123"},
    )
    assert allowed.status_code == 200
    assert "access_token" in allowed.json()


@pytest.mark.django_db
def test_settings_page_shows_pairing_qr(django_client, user):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    page = django_client.get("/app/settings/")
    assert page.status_code == 200
    assert b"POS tablet pairing" in page.content
    assert b"API key" in page.content
    assert b"Receipt header" in page.content
    assert b"Store name" in page.content
    qr = django_client.get("/app/settings/pos-qr.png")
    assert qr.status_code == 200
    assert qr["Content-Type"] == "image/png"
    assert qr.content.startswith(b"\x89PNG")


@pytest.mark.django_db
def test_settings_page_saves_receipt_header(django_client, user, branch):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    page = django_client.post(
        "/app/settings/",
        {
            "intent": "receipt",
            f"receipt_store_name_{branch.id}": "Pickleball West",
            f"receipt_address_{branch.id}": "88 West Avenue, QC",
        },
    )
    assert page.status_code == 302
    branch.refresh_from_db()
    assert branch.receipt_store_name == "Pickleball West"
    assert branch.receipt_address == "88 West Avenue, QC"


@pytest.mark.django_db
def test_settings_page_saves_void_passcode(django_client, user, branch):
    assert django_client.login(username="cashier1", password="secure-pass-123")
    page = django_client.post(
        "/app/settings/",
        {
            "intent": "void_passcode",
            f"void_passcode_{branch.id}": "2468",
        },
    )
    assert page.status_code == 302
    branch.refresh_from_db()
    assert branch.void_passcode_set
    from core.services.sale_service import SaleService

    SaleService.verify_void_passcode(branch, "2468")
