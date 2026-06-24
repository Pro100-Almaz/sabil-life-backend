"""
Review signals — Phase 7.

Fires recompute_listing_rating() after any Review is saved or deleted so
the Listing's denormalized rating/review_count stays in sync.

Wired in ReviewsConfig.ready() (apps.py).
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.reviews.models import Review
from apps.reviews.services import recompute_listing_rating


@receiver([post_save, post_delete], sender=Review)
def trigger_rating_recompute(sender, instance: Review, **kwargs) -> None:
    """Recompute the parent listing's rating whenever a review changes."""
    recompute_listing_rating(instance.listing)
