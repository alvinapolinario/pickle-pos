import pytest


def _auth_headers(api_client):
    login = api_client.post(
        "/api/v1/auth/login",
        json={"username": "cashier1", "password": "secure-pass-123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.mark.django_db(transaction=True)
def test_vat_setting_defaults_on_and_can_be_turned_off(api_client, user, branch):
    headers = _auth_headers(api_client)
    current = api_client.get("/api/v1/settings", headers=headers)
    assert current.status_code == 200
    assert current.json()["vat_registered"] is True
    assert current.json()["branch_id"] == branch.id

    updated = api_client.patch("/api/v1/settings", json={"vat_registered": False}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["vat_registered"] is False
    branch.refresh_from_db()
    assert branch.vat_registered is False
