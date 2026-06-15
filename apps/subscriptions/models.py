"""
MasterclassSubscription model — Phase 5 MASTERCLASSES auto-confirm flow.

A family subscribes to a MASTERCLASSES listing and is immediately confirmed.
No provider accept/decline step — the whole point is auto-confirm.

Snapshot semantics: `provider` is denormalized from listing.owner at creation
time. If an admin later reassigns the listing to a different owner, existing
subscriptions still point at the original provider.

Uniqueness approach:
  We use a conditional UniqueConstraint(condition=Q(status="CONFIRMED")) rather
  than a database-level unique_together. This means:
    - A family cannot have two CONFIRMED subscriptions for the same listing.
    - After cancellation (status=CANCELLED), they may re-subscribe.
    - Cancelled rows are retained for audit purposes (soft cancel, not hard delete).

Re-subscribe: DELETE on the API sets status=CANCELLED + cancelled_at=now().
The conditional constraint allows a fresh subscription row to be created.
"""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class SubscriptionStatus(models.TextChoices):
    CONFIRMED = "CONFIRMED", _("Confirmed")
    CANCELLED = "CANCELLED", _("Cancelled")


class MasterclassSubscription(models.Model):
    """
    Auto-confirmed subscription to a MASTERCLASSES listing.

    State transitions:
      CONFIRMED → CANCELLED (via family DELETE on /subscriptions/{id}/)
      No re-activate from CANCELLED — family must create a new subscription.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    listing = models.ForeignKey(
        "catalog.Listing",
        on_delete=models.PROTECT,
        related_name="subscriptions",
    )
    # Denormalized snapshot of listing.owner at creation time — see module docstring.
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_subscriptions",
    )
    status = models.CharField(
        max_length=16,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.CONFIRMED,
        db_index=True,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["family", "listing"],
                condition=Q(status="CONFIRMED"),
                name="unique_active_subscription",
            )
        ]

    def __str__(self) -> str:
        return f"Subscription {self.id} ({self.status})"
