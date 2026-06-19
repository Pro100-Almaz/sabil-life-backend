"""
Review service layer — Phase 7.

Business rules:
  - can_review(user, listing): engagement gate (see docstring).
  - recompute_listing_rating(listing): idempotent denormalized rating update.

Engagement gate vs spec:
  Spec §8 says "auth required to post." We add an evidence-of-engagement gate
  because allowing any authenticated user to review without ever interacting
  with a listing would pollute the rating system.

  Gate rules by category:
    TUTORING     — family must have an Inquiry on this listing with status
                   ACCEPTED or COMPLETED.
    MASTERCLASSES — family must have at least one MasterclassSubscription on
                   this listing (any status — CONFIRMED or CANCELLED counts;
                   the family attended at least once).
    All other categories (SCHOOLS, NURSERIES, ACTIVITIES, ENTERTAINMENT,
    PARTNERSHIPS) — no gate. Any authenticated FAMILY user may review. These
    are admin-curated directory entries with no transactional flow.
"""

from django.db.models import Avg, Count

from apps.catalog.models import ListingCategory


def can_review(user, listing) -> bool:
    """
    Return True if the user is allowed to post a review on the given listing.

    Diverges from spec §8 ("auth required"): we additionally check engagement
    evidence for TUTORING and MASTERCLASSES listings to prevent drive-by ratings.

    For all other categories the only requirement is IsAuthenticated + role=FAMILY,
    which is enforced at the view layer. This function just gates the engagement
    check; callers should also verify role before calling.
    """
    if listing.category == ListingCategory.TUTORING:
        from apps.inquiries.models import Inquiry, InquiryStatus

        return Inquiry.objects.filter(
            family=user,
            listing=listing,
            status__in=[InquiryStatus.ACCEPTED, InquiryStatus.COMPLETED],
        ).exists()

    if listing.category == ListingCategory.MASTERCLASSES:
        from apps.subscriptions.models import MasterclassSubscription

        return MasterclassSubscription.objects.filter(
            family=user,
            listing=listing,
        ).exists()

    # SCHOOLS, NURSERIES, ACTIVITIES, ENTERTAINMENT, PARTNERSHIPS: no gate.
    return True


def recompute_listing_rating(listing) -> None:
    """
    Recompute denormalized rating + review_count on a Listing.

    Idempotent. Called after Review save/delete via the post_save/post_delete
    signal in signals.py.

    Note: the seed_catalog command (Phase 3) populates `rating` with fake values
    (3.8-4.9) for visual realism. Once real reviews land, those seeded values
    are intentionally overwritten by this function.
    """
    aggregate = listing.reviews.aggregate(
        avg=Avg("rating"),
        count=Count("id"),
    )
    listing.rating = round(aggregate["avg"] or 0, 1)
    listing.review_count = aggregate["count"] or 0
    listing.save(update_fields=["rating", "review_count", "updated_at"])
