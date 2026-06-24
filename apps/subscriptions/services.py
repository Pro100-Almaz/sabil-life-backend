"""
Subscription service layer — Phase 5.
"""

from apps.catalog.models import Listing, ListingCategory, ListingStatus

from apps.subscriptions.models import MasterclassSubscription, SubscriptionStatus


class DuplicateSubscription(Exception):
    """Raised when a CONFIRMED subscription already exists for (family, listing)."""


def create_subscription(family, listing: Listing) -> MasterclassSubscription:
    """
    Create a new CONFIRMED subscription for a MASTERCLASSES listing.

    Validates:
    - listing is ACTIVE
    - listing category is MASTERCLASSES
    - no existing CONFIRMED subscription for (family, listing)

    Snapshots provider = listing.owner at creation time.
    """
    if listing.status != ListingStatus.ACTIVE:
        raise ValueError("Listing is not active.")
    if listing.category != ListingCategory.MASTERCLASSES:
        raise ValueError(
            "Subscriptions only allowed on MASTERCLASSES listings; "
            "use /inquiries/ for tutoring."
        )
    if listing.owner_id is None:
        raise ValueError(
            "Listing has no provider assigned and cannot accept subscriptions."
        )
    if MasterclassSubscription.objects.filter(
        family=family,
        listing=listing,
        status=SubscriptionStatus.CONFIRMED,
    ).exists():
        raise DuplicateSubscription(
            "You already have an active subscription for this listing."
        )
    return MasterclassSubscription.objects.create(
        family=family,
        listing=listing,
        provider=listing.owner,
        status=SubscriptionStatus.CONFIRMED,
    )
