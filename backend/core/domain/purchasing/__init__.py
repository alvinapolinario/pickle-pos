"""Purchase order workflow constants."""

DRAFT = "draft"
ORDERED = "ordered"
PARTIAL = "partial"
RECEIVED = "received"
CANCELLED = "cancelled"

PO_STATUSES = (DRAFT, ORDERED, PARTIAL, RECEIVED, CANCELLED)
RECEIVABLE_STATUSES = frozenset({ORDERED, PARTIAL})
EDITABLE_STATUSES = frozenset({DRAFT})
