# Pickle POS — Android Application

Flutter POS app will be initialized in Phase 4.

## Planned structure

```
lib/
├── main.dart
├── app/
├── core/
│   ├── auth/
│   ├── database/     # Drift SQLite
│   ├── network/
│   └── printing/
├── features/
│   ├── login/
│   ├── shift/
│   ├── pos/
│   ├── payment/
│   └── sync/
└── sync/
    ├── sync_engine.dart
    └── push_queue.dart
```

## Screens

Login → Open Shift → POS Home → Checkout → Payment → Receipt

See [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) for full mobile design.
