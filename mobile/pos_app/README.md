# Pickle POS — Android cashier app

Flutter POS client for the FastAPI mobile API.

## Run

```bash
cd mobile/pos_app
flutter pub get
flutter run
```

Default API URL is `http://10.0.2.2:7101` (Android emulator → host). Change it in **Settings**.

| Environment | API URL |
|-------------|---------|
| Android emulator | `http://10.0.2.2:7101` |
| iOS simulator | `http://127.0.0.1:7101` |
| Physical device | `http://<lan-ip>:7101` |

Sign in with a cashier account (same as the web console). Register a device code on first login.

## Screens

Login → Open shift → POS (catalog + cart) → Checkout → Receipt

Also: Tickets (completed / held / void / refund), Court bookings, Shift close, Settings (API URL, device code, VAT, pending sync).

Prices and totals always come from the server (`POST /sales/quote`, `POST /sales`). Offline tickets are queued locally and pushed with `POST /sync/push`.
