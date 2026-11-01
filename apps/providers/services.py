import logging

from django.db import transaction

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


def apply_ownership_outcome(ownership: ListingOwnershipRequest, reviewer=None) -> bool:
    """
    Apply a reviewed ownership request. Approving makes the requester the
    listing's owner and closes every other pending request for that listing.
    """
    approved = ownership.status == StatusChoices.APPROVED

    if approved:
        with transaction.atomic():
            listing = ownership.listing
            listing.owner = ownership.user
            listing.save(update_fields=["owner", "updated_at"])
            ListingOwnershipRequest.objects.filter(
                listing=listing, status=StatusChoices.PENDING
            ).exclude(pk=ownership.pk).update(
                status=StatusChoices.REJECTED,
                comment="Another provider was approved for this listing.",
            )

    logger.info(
        "Reviewer %s set ownership request %s (%s, listing %s) to %s.",
        getattr(reviewer, "email", "system"),
        ownership.pk,
        ownership.user.email,
        ownership.listing_id,
        ownership.status,
    )

    from apps.notifications.tasks import notify_ownership_result

    transaction.on_commit(lambda: notify_ownership_result.delay(ownership.pk))
    return approved
