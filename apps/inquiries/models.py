"""
Inquiry model — Phase 5 TUTORING flow.

An Inquiry represents a family's request to connect with a TUTORING listing's
provider. Only TUTORING listings participate in the inquiry flow; MASTERCLASSES
use MasterclassSubscription instead.

Snapshot semantics: `provider` is denormalized from listing.owner at creation
time. If an admin later reassigns the listing to a different owner, existing
inquiries still point at the original provider so the audit trail stays intact.

# commission FK added in Phase 6 billing app
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class InquiryStatus(models.TextChoices):
    NEW = "NEW", _("New")
    CONTACTED = "CONTACTED", _("Contacted")
    ACCEPTED = "ACCEPTED", _("Accepted")
    DECLINED = "DECLINED", _("Declined")
    COMPLETED = "COMPLETED", _("Completed")


class Inquiry(models.Model):
    """
    Represents a family's inquiry to a TUTORING listing provider.

    State machine (managed by services.transition):
        NEW → CONTACTED, ACCEPTED, DECLINED
        CONTACTED → ACCEPTED, DECLINED
        ACCEPTED → COMPLETED
        DECLINED, COMPLETED → terminal

    The `contact_revealed` flag is always False in Phase 5.
    Phase 6 (billing/subscription gate) will flip it when the family's
    subscription tier grants contact reveal.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    family = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inquiries",
    )
    listing = models.ForeignKey(
        "catalog.Listing",
        on_delete=models.PROTECT,
        related_name="inquiries",
    )
    # Denormalized snapshot of listing.owner at creation time — see module docstring.
    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_inquiries",
    )
    message = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=InquiryStatus.choices,
        default=InquiryStatus.NEW,
        db_index=True,
    )
    contact_revealed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Inquiry {self.id} ({self.status})"
