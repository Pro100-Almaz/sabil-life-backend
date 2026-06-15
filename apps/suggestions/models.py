"""
ServiceSuggestion model — Phase 5 family→admin sourcing channel.

Families submit service suggestions (e.g. "We'd love a pottery class in Lusail").
Admins review and act on them via the Django admin panel only — no REST endpoints
for admin management.

Role-gating decision: only FAMILY users may submit suggestions via the API.
Other roles (TUTOR, MASTERCLASS, ADMIN) are rejected with 403. Rationale:
  - Providers suggest services via the provider self-service listing flow.
  - Admins manage the platform directly and don't need to suggest to themselves.
  - FAMILY is the target persona for sourcing new services.

`admin_notes` is an internal field — never exposed on the family-facing API
endpoints (enforced in the serializer's explicit field list).
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import ListingCategory


class SuggestionStatus(models.TextChoices):
    NEW = "NEW", _("New")
    REVIEWED = "REVIEWED", _("Reviewed")
    ACTED_ON = "ACTED_ON", _("Acted on")
    DISMISSED = "DISMISSED", _("Dismissed")


class ServiceSuggestion(models.Model):
    """
    A family's request for a new service to be sourced by the Sabil Life team.
    """

    family = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="suggestions",
    )
    # Optional hint fields — family may leave either blank.
    category = models.CharField(
        max_length=32,
        choices=ListingCategory.choices,
        blank=True,
        default="",
    )
    neighborhood = models.CharField(max_length=120, blank=True, default="")
    message = models.TextField()
    status = models.CharField(
        max_length=16,
        choices=SuggestionStatus.choices,
        default=SuggestionStatus.NEW,
        db_index=True,
    )
    # Internal admin field — NEVER exposed on family API.
    admin_notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        preview = self.message[:60]
        return f"Suggestion by {self.family_id}: {preview}"
