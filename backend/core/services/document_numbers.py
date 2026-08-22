"""Allocate sequential document numbers per branch and prefix."""

from django.utils import timezone


def next_document_number(model, branch_id: int, field: str, prefix: str) -> str:
    stem = f"{prefix}-{timezone.localdate().strftime('%Y%m%d')}-"
    last = (
        model.objects.select_for_update()
        .filter(branch_id=branch_id, **{f"{field}__startswith": stem})
        .order_by(f"-{field}")
        .values_list(field, flat=True)
        .first()
    )
    seq = int(last.rsplit("-", 1)[-1]) + 1 if last else 1
    return f"{stem}{seq:04d}"
