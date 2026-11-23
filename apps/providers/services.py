import logging
from functools import partial

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Listing, ListingStatus
from apps.catalog.tasks import delete_storage_objects
from apps.providers.models import (
    AvatarImage,
    ListingOwnershipRequest,
    ProviderChoices,
    ProviderVerification,
    StatusChoices,
    TutorDetail,
)
from apps.users.models import Role

logger = logging.getLogger(__name__)


def apply_verification_outcome(verification: ProviderVerification, reviewer=None) -> bool:
    approved = verification.status == StatusChoices.APPROVED
    user = verification.user

    role, _ = Role.objects.get_or_create(name=verification.provider_type)
    if approved:
        user.roles.add(role)
    else:
        user.roles.remove(role)
    if hasattr(user, "_role_names_cache"):
        del user._role_names_cache

        # Keep TutorDetail's mirror flag truthful for the tutor-detail API.
    if verification.provider_type == ProviderChoices.TUTOR:
        TutorDetail.objects.filter(user=user, deleted_at__isnull=True).update(
            is_verified=approved
        )

    logger.info(
        "Reviewer %s set %s verification for %s to %s (role %s).",
        getattr(reviewer, "email", "system"),
        verification.provider_type,
        user.email,
        verification.status,
        "granted" if approved else "revoked",
    )

    # Fire-and-forget: notify the applicant of the outcome. Imported locally to
    # avoid an app-loading circular import; .delay() keeps the admin action from
    # blocking on (or breaking because of) push delivery.
    from apps.notifications.tasks import notify_verification_result

    notify_verification_result.delay(verification.id)

    return approved


def delete_avatar_image(avatar: AvatarImage) -> None:
    key = avatar.key
    avatar.delete()
    if key:
        transaction.on_commit(lambda: delete_storage_objects.delay([key]))


class OwnershipReviewError(Exception):
    """The ownership request can no longer be reviewed as asked."""


def review_ownership_request(
    ownership_id: int, status: str, comment: str = "", reviewer=None
) -> ListingOwnershipRequest:
    """
    Decide a pending ownership request safely under concurrency.

    The listing row is locked first so every review touching the same listing is
    serialized (locking the listing before the request avoids deadlocks with the
    sibling auto-rejection). The request's state and the listing are then
    re-checked under the lock.
    """
    listing_id = (
        ListingOwnershipRequest.objects.filter(pk=ownership_id)
        .values_list("listing_id", flat=True)
        .first()
    )
    if listing_id is None:
        raise OwnershipReviewError("Ownership request not found.")

    with transaction.atomic():
        listing = Listing.objects.select_for_update().get(pk=listing_id)
        ownership = ListingOwnershipRequest.objects.select_for_update().get(
            pk=ownership_id
        )
        if ownership.status != StatusChoices.PENDING:
            raise OwnershipReviewError("Only pending requests can be reviewed.")
        if status == StatusChoices.APPROVED:
            if listing.status != ListingStatus.ACTIVE:
                raise OwnershipReviewError("The listing is no longer active.")
            if listing.owner_id == ownership.user_id:
                raise OwnershipReviewError("The requester already owns this listing.")

        ownership.listing = listing
        ownership.status = status
        ownership.comment = comment
        ownership.save(update_fields=["status", "comment", "updated_at"])
        apply_ownership_outcome(ownership, reviewer)
    return ownership


def apply_ownership_outcome(ownership: ListingOwnershipRequest, reviewer=None) -> bool:
    """
    Apply a reviewed ownership request. Approving makes the requester the
    listing's owner and closes (and notifies) every other pending request for
    that listing. Call via review_ownership_request, which holds the locks.
    """
    from apps.notifications.tasks import notify_ownership_result

    approved = ownership.status == StatusChoices.APPROVED
    notify_ids = [ownership.pk]

    if approved:
        with transaction.atomic():
            listing = ownership.listing
            listing.owner = ownership.user
            listing.save(update_fields=["owner", "updated_at"])
            siblings = ListingOwnershipRequest.objects.filter(
                listing=listing, status=StatusChoices.PENDING
            ).exclude(pk=ownership.pk)
            sibling_ids = list(siblings.values_list("pk", flat=True))
            if sibling_ids:
                ListingOwnershipRequest.objects.filter(pk__in=sibling_ids).update(
                    status=StatusChoices.REJECTED,
                    comment="Another provider was approved for this listing.",
                    updated_at=timezone.now(),
                )
            notify_ids.extend(sibling_ids)

    logger.info(
        "Reviewer %s set ownership request %s (%s, listing %s) to %s.",
        getattr(reviewer, "email", "system"),
        ownership.pk,
        ownership.user.email,
        ownership.listing_id,
        ownership.status,
    )

    for request_id in notify_ids:
        transaction.on_commit(
            partial(notify_ownership_result.delay, request_id), robust=True
        )
    return approved
