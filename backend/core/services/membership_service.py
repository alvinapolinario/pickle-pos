"""Membership benefits, feature flag, and loyalty ledger."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from core.domain.pricing import money


@dataclass(frozen=True)
class MembershipBenefits:
    membership_id: int
    customer_id: int
    tier_id: int
    tier_code: str
    tier_name: str
    court_discount_pct: Decimal
    canteen_discount_pct: Decimal
    priority_booking: bool
    points_per_peso: Decimal
    loyalty_points: int


class MembershipService:
    def enabled(self, branch_id: int | None) -> bool:
        if not branch_id:
            return False
        from apps.branches.models import Branch

        branch = Branch.objects.filter(pk=branch_id).only("memberships_enabled").first()
        return bool(branch and branch.memberships_enabled)

    def benefits_for(self, *, branch_id: int | None, customer_id: int | None, on_date: date | None = None) -> MembershipBenefits | None:
        if not branch_id or not customer_id or not self.enabled(branch_id):
            return None
        from apps.customers.models import Customer
        from apps.membership.models import Membership

        today = on_date or timezone.localdate()
        membership = (
            Membership.objects.select_related("tier", "customer")
            .filter(
                branch_id=branch_id,
                customer_id=customer_id,
                status=Membership.Status.ACTIVE,
                started_on__lte=today,
            )
            .filter(models_q_expires(today))
            .order_by("-started_on", "-id")
            .first()
        )
        if membership is None:
            return None
        customer = membership.customer if membership.customer_id else Customer.objects.filter(pk=customer_id).first()
        return MembershipBenefits(
            membership_id=membership.id,
            customer_id=customer_id,
            tier_id=membership.tier_id,
            tier_code=membership.tier.code,
            tier_name=membership.tier.name,
            court_discount_pct=membership.tier.court_discount_pct,
            canteen_discount_pct=membership.tier.canteen_discount_pct,
            priority_booking=membership.tier.priority_booking,
            points_per_peso=membership.tier.points_per_peso,
            loyalty_points=customer.loyalty_points if customer else 0,
        )

    def canteen_discount(self, *, branch_id: int, customer_id: int | None, gross: Decimal) -> Decimal:
        benefits = self.benefits_for(branch_id=branch_id, customer_id=customer_id)
        if benefits is None or benefits.canteen_discount_pct <= 0:
            return money(0)
        return money(Decimal(str(gross)) * benefits.canteen_discount_pct / Decimal("100"))

    def apply_court_rate(self, *, branch_id: int, customer_id: int | None, amount: Decimal) -> Decimal:
        benefits = self.benefits_for(branch_id=branch_id, customer_id=customer_id)
        priced = money(amount)
        if benefits is None or benefits.court_discount_pct <= 0:
            return priced
        return money(priced - priced * benefits.court_discount_pct / Decimal("100"))

    def assign(
        self,
        *,
        branch_id: int,
        customer_id: int,
        tier_id: int,
        started_on: date | None = None,
        expires_on: date | None = None,
        notes: str = "",
    ):
        from apps.customers.models import Customer
        from apps.membership.models import Membership, MembershipTier

        customer = Customer.objects.filter(pk=customer_id, branch_id=branch_id).first()
        if customer is None:
            from core.domain.exceptions import NotFoundError

            raise NotFoundError("Customer not found for this branch.")
        tier = MembershipTier.objects.filter(pk=tier_id, branch_id=branch_id, is_active=True).first()
        if tier is None:
            from core.domain.exceptions import NotFoundError

            raise NotFoundError("Membership tier not found.")
        start = started_on or timezone.localdate()
        with transaction.atomic():
            Membership.objects.filter(
                customer_id=customer_id,
                branch_id=branch_id,
                status=Membership.Status.ACTIVE,
            ).update(status=Membership.Status.CANCELLED, updated_at=timezone.now())
            membership = Membership.objects.create(
                branch_id=branch_id,
                customer=customer,
                tier=tier,
                started_on=start,
                expires_on=expires_on,
                notes=notes,
            )
        from apps.audit.middleware import write_audit_log

        write_audit_log(
            action="membership.assign",
            entity_type="membership",
            entity_id=str(membership.id),
            new_values={"customer_id": customer_id, "tier": tier.code},
        )
        return membership

    def award_points(
        self,
        *,
        customer_id: int | None,
        branch_id: int,
        amount: Decimal,
        source_type: str,
        source_id: int,
        notes: str = "",
    ) -> int:
        benefits = self.benefits_for(branch_id=branch_id, customer_id=customer_id)
        if benefits is None or benefits.points_per_peso <= 0 or not customer_id:
            return 0
        points = int(money(amount) * benefits.points_per_peso)
        if points <= 0:
            return 0
        self._post_points(
            customer_id=customer_id,
            branch_id=branch_id,
            points=points,
            kind="earn",
            source_type=source_type,
            source_id=source_id,
            notes=notes,
        )
        return points

    def clawback_points(
        self,
        *,
        customer_id: int | None,
        branch_id: int,
        amount: Decimal,
        source_type: str,
        source_id: int,
        notes: str = "",
    ) -> int:
        benefits = self.benefits_for(branch_id=branch_id, customer_id=customer_id)
        if benefits is None or benefits.points_per_peso <= 0 or not customer_id:
            return 0
        points = int(money(amount) * benefits.points_per_peso)
        if points <= 0:
            return 0
        self._post_points(
            customer_id=customer_id,
            branch_id=branch_id,
            points=-points,
            kind="reverse",
            source_type=source_type,
            source_id=source_id,
            notes=notes,
        )
        return points

    def reverse_points(self, *, source_type: str, source_id: int, notes: str = "") -> int:
        from apps.membership.models import LoyaltyTransaction

        earned = list(
            LoyaltyTransaction.objects.filter(source_type=source_type, source_id=source_id, kind=LoyaltyTransaction.Kind.EARN)
        )
        if not earned:
            return 0
        already = LoyaltyTransaction.objects.filter(
            source_type=f"{source_type}_reverse",
            source_id=source_id,
        ).exists()
        if already:
            return 0
        total = 0
        for row in earned:
            self._post_points(
                customer_id=row.customer_id,
                branch_id=row.branch_id,
                points=-row.points,
                kind="reverse",
                source_type=f"{source_type}_reverse",
                source_id=source_id,
                notes=notes or f"Reverse {source_type} #{source_id}",
            )
            total += row.points
        return total

    def _post_points(
        self,
        *,
        customer_id: int,
        branch_id: int,
        points: int,
        kind: str,
        source_type: str,
        source_id: int,
        notes: str,
    ) -> None:
        from apps.customers.models import Customer
        from apps.membership.models import LoyaltyTransaction

        with transaction.atomic():
            LoyaltyTransaction.objects.create(
                branch_id=branch_id,
                customer_id=customer_id,
                points=points,
                kind=kind,
                source_type=source_type,
                source_id=source_id,
                notes=notes,
            )
            Customer.objects.filter(pk=customer_id).update(loyalty_points=F("loyalty_points") + points)


def models_q_expires(today: date):
    from django.db.models import Q

    return Q(expires_on__isnull=True) | Q(expires_on__gte=today)
