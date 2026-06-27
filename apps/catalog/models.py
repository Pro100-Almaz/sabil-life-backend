import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ListingCategory(models.TextChoices):
    SCHOOLS = "SCHOOLS", _("Schools")
    NURSERIES = "NURSERIES", _("Nurseries")
    ACTIVITIES = "ACTIVITIES", _("Activities")
    ENTERTAINMENT = "ENTERTAINMENT", _("Entertainment")
    TUTORING = "TUTORING", _("Tutoring")
    MASTERCLASSES = "MASTERCLASSES", _("Masterclasses")
    PARTNERSHIPS = "PARTNERSHIPS", _("Partnerships")


class ListingStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    PENDING = "PENDING", _("Pending")
    ACTIVE = "ACTIVE", _("Active")
    REJECTED = "REJECTED", _("Rejected")


class ListingClientStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    ACCEPTED = "ACCEPTED", _("Accepted")
    REJECTED = "REJECTED", _("Rejected")


class Listing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    category = models.CharField(
        max_length=32,
        choices=ListingCategory.choices,
        db_index=True,
    )
    subtitle = models.CharField(max_length=300, blank=True)
    neighborhood = models.CharField(max_length=120, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    price_from_qar = models.PositiveIntegerField(default=0)
    age_groups = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    highlights = models.JSONField(default=list, blank=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=Decimal("0.0"))
    review_count = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False, db_index=True)
    status = models.CharField(
        max_length=16,
        choices=ListingStatus.choices,
        default=ListingStatus.DRAFT,
        db_index=True,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="listings",
    )
    # --- Phase 5 private fields (never exposed on public catalog endpoints) ---
    session_schedule = models.TextField(blank=True, default="")
    exact_address = models.TextField(blank=True, default="")
    materials_required = models.JSONField(default=list, blank=True)
    # -------------------------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_featured", "-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.category})"


class ListingClient(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listing_requests",
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="clients",
    )
    status = models.CharField(
        choices=ListingClientStatus.choices,
        default=ListingClientStatus.PENDING,
        max_length=40,
    )
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "listing"],
                name="unique_listing_client_per_user",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.listing} ({self.status})"
    

class ListingImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="images" 
    )
    key = models.CharField(max_length=512, unique=True) #identity 
    position = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["listing", "position"],
                name="unique_listing_image",
            )
        ]

    def __str__(self):
        return self.key
