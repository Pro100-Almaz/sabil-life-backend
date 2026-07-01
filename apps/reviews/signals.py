"""
Review signals — Phase 7.

Fires recompute_listing_rating() after any Review is saved or deleted so
the Listing's denormalized rating/review_count stays in sync.

Wired in ReviewsConfig.ready() (apps.py).
"""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.reviews.models import Review, TutorReview
from apps.reviews.services import recompute_listing_rating, recompute_tutor_rating


@receiver([post_save, post_delete], sender=Review)
def trigger_rating_recompute(sender, instance: Review, **kwargs) -> None:
    """Recompute the parent listing's rating whenever a review changes."""
    recompute_listing_rating(instance.listing)


@receiver([post_save, post_delete], sender=TutorReview)
def trigger_tutor_rating_recompute(sender, instance: TutorReview, **kwargs) -> None:
    """Recompute the tutor's rating/review_count whenever a tutor review changes."""
    recompute_tutor_rating(instance.tutor)
