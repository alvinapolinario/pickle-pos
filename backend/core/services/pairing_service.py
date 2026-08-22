"""POS tablet pairing: API URL + key encoded as a QR payload."""

from __future__ import annotations

import hmac
import io
import json
import secrets
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlparse

from core.config.settings import get_settings

SCHEME = "picklepos"
HEADER = "X-Api-Key"


@dataclass(frozen=True)
class PairingInfo:
    api_key: str
    public_base_url: str
    payload: str


def generate_api_key() -> str:
    return secrets.token_urlsafe(24)


def normalize_base_url(url: str) -> str:
    return url.strip().rstrip("/")


def default_public_url(request=None) -> str:
    configured = get_settings().public_api_url.strip()
    if configured:
        return normalize_base_url(configured)
    if request is not None:
        host = request.get_host().split(":")[0]
        if host:
            return f"http://{host}:7101"
    return "http://127.0.0.1:7101"


def encode_payload(url: str, key: str) -> str:
    return f"{SCHEME}://connect?{urlencode({'url': normalize_base_url(url), 'key': key})}"


def parse_payload(raw: str) -> tuple[str, str] | None:
    text = (raw or "").strip()
    if not text:
        return None
    if text.startswith("{"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        url = normalize_base_url(str(data.get("url") or ""))
        key = str(data.get("key") or "").strip()
        return (url, key) if url and key else None

    parsed = urlparse(text)
    query = {name: values[0] for name, values in parse_qs(parsed.query).items() if values}
    if parsed.scheme == SCHEME and parsed.netloc == "connect":
        url = normalize_base_url(query.get("url", ""))
        key = query.get("key", "").strip()
        return (url, key) if url and key else None
    if "url" in query and "key" in query:
        url = normalize_base_url(query["url"])
        key = query["key"].strip()
        return (url, key) if url and key else None
    return None


def keys_match(provided: str | None, expected: str) -> bool:
    if not provided or not expected:
        return False
    left = provided.encode("utf-8")
    right = expected.encode("utf-8")
    if len(left) != len(right):
        return False
    return hmac.compare_digest(left, right)


def qr_png_bytes(payload: str) -> bytes:
    import qrcode

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class PairingService:
    def get_or_create(self, request=None) -> PairingInfo:
        from apps.accounts.models import PosConnection

        row, created = PosConnection.objects.get_or_create(
            pk=PosConnection.SINGLETON_PK,
            defaults={
                "api_key": get_settings().mobile_api_key.strip() or generate_api_key(),
                "public_base_url": default_public_url(request),
            },
        )
        if created is False and not row.public_base_url:
            row.public_base_url = default_public_url(request)
            row.save(update_fields=["public_base_url", "updated_at"])
        url = normalize_base_url(row.public_base_url) or default_public_url(request)
        return PairingInfo(api_key=row.api_key, public_base_url=url, payload=encode_payload(url, row.api_key))

    def save_public_url(self, url: str, request=None) -> PairingInfo:
        from apps.accounts.models import PosConnection

        info = self.get_or_create(request=request)
        row = PosConnection.objects.get(pk=PosConnection.SINGLETON_PK)
        row.public_base_url = normalize_base_url(url) or info.public_base_url
        row.save(update_fields=["public_base_url", "updated_at"])
        return self.get_or_create(request=request)

    def regenerate(self, request=None) -> PairingInfo:
        from apps.accounts.models import PosConnection

        self.get_or_create(request=request)
        row = PosConnection.objects.get(pk=PosConnection.SINGLETON_PK)
        row.api_key = generate_api_key()
        row.save(update_fields=["api_key", "updated_at"])
        return self.get_or_create(request=request)

    def current_key(self) -> str | None:
        from apps.accounts.models import PosConnection

        row = PosConnection.objects.filter(pk=PosConnection.SINGLETON_PK).first()
        if row and row.api_key:
            return row.api_key
        env_key = get_settings().mobile_api_key.strip()
        return env_key or None
