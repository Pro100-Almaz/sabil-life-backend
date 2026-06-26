"""
Inquiry model — family-to-tutor request flow.

An Inquiry represents a family's request to connect with a *tutor*. It is not
tied to a listing or a masterclass: the family addresses a specific tutor
directly via that tutor's TutorDetail profile. Masterclass providers do not
participate in the inquiry flow at all (they use MasterclassSubscription).

Roles:
    FAMILY — creates an inquiry (with a message) and may cancel it.
    TUTOR  — sees inquiries addressed to them and updates their status.
    MASTERCLASS / ADMIN / MANAGER — no inquiry endpoints.

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
    CANCELLED = "CANCELLED", _("Cancelled")


class Inquiry(models.Model):
    """
    Represents a family's inquiry addressed to a tutor.

    State machine (managed by services.transition):
        NEW       → CONTACTED, ACCEPTED, DECLINED, CANCELLED
        CONTACTED → ACCEPTED, DECLINED, CANCELLED
        ACCEPTED  → COMPLETED
        DECLINED, COMPLETED, CANCELLED → terminal

    Tutor-driven transitions: CONTACTED, ACCEPTED, DECLINED, COMPLETED.
    Family-driven transition:  CANCELLED.

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
    tutor = models.ForeignKey(
        "providers.TutorDetail",
        on_delete=models.PROTECT,
        related_name="inquiries",
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
