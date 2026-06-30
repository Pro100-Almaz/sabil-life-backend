"""
Review model — Phase 7.

One review per (listing, author) pair, enforced via UniqueConstraint.
Reviews drive the denormalized rating/review_count on Listing via a
post_save/post_delete signal (see signals.py).

No TimeStampedModel mixin exists in this codebase yet — Phases 1-5
added created_at/updated_at inline everywhere. We continue that pattern.
"""

import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        "catalog.Listing",
        on_delete=models.PROTECT,
        related_name="reviews",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviews_written",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    text = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("review")
        verbose_name_plural = _("reviews")
        constraints = [
            models.UniqueConstraint(
                fields=["listing", "author"],
                name="unique_review_per_listing_author",
            ),
        ]

    def __str__(self) -> str:
        return f"Review({self.listing_id}, author={self.author_id}, rating={self.rating})"


class TutorReview(models.Model):
    """
    A family's review of a tutor (TutorDetail), mirroring Review for listings.

    One review per (tutor, author) pair, enforced via UniqueConstraint.
    Reviews drive the denormalized rating/review_count on TutorDetail via a
    post_save/post_delete signal (see signals.py).

    A review may only be created when the family has an Inquiry with this tutor
    in CONTACTED / ACCEPTED / COMPLETED (see services.can_review_tutor).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tutor = models.ForeignKey(
        "providers.TutorDetail",
        on_delete=models.PROTECT,
        related_name="tutor_reviews",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tutor_reviews_written",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    text = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("tutor review")
        verbose_name_plural = _("tutor reviews")
        constraints = [
            models.UniqueConstraint(
                fields=["tutor", "author"],
                name="unique_review_per_tutor_author",
            ),
        ]

    def __str__(self) -> str:
        return f"TutorReview({self.tutor_id}, author={self.author_id}, rating={self.rating})"
