import logging

from celery import shared_task
from django.utils.translation import gettext as _

from apps.catalog.models import Event, Listing, ListingStatus
from apps.core.tasks import BaseTaskWithRetry
from apps.inquiries.models import Inquiry, InquiryStatus
from apps.notifications.models import Notification, NotificationType
from apps.notifications.services import notify_user, send_push_to_user
from apps.providers.models import (
    ListingOwnershipRequest,
    ProviderFollow,
    ProviderVerification,
    StatusChoices,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, base=BaseTaskWithRetry, soft_time_limit=270, time_limit=300)
def notify_provider_event(self, event_id: str, provider_id: int) -> None:
    """Deliver one inbox entry per follower; pushes remain best effort."""
    event = Event.objects.filter(pk=event_id).first()
    if event is None:
        logger.info("Event %s no longer exists; skipping", event_id)
        return
    follows = ProviderFollow.objects.filter(
        provider_id=provider_id,
        created_at__lte=event.published_at,
        client__is_active=True,
        client__deleted_at__isnull=True,
    ).select_related("client", "provider")
    data = {
        "event_id": str(event.pk),
        "listing_id": str(event.listing_id),
    }
    for follow in follows.iterator(chunk_size=500):
        data["provider_id"] = str(follow.provider.uuid)
        notification, created = Notification.objects.get_or_create(
            user=follow.client,
            event=event,
            defaults={
                "type": NotificationType.PROVIDER_EVENT,
                "title": _("New provider event"),
                "body": event.title,
                "data": data,
            },
        )
        if created:
            try:
                send_push_to_user(
                    follow.client,
                    notification.title,
                    notification.body,
                    notification.data,
                )
            except Exception:
                logger.exception(
                    "Push failed for event %s, user %s", event_id, follow.client_id
                )


ProviderResponse = {
    InquiryStatus.ACCEPTED,
    InquiryStatus.DECLINED,
}


@shared_task(bind=True, base=BaseTaskWithRetry)
def notify_admin_created_inquiry(self, inquiry_id: str) -> None:
    """Notify both parties when an administrator creates an inquiry."""
    try:
        inquiry = Inquiry.objects.select_related("family", "tutor__user").get(
            id=inquiry_id
        )
    except Inquiry.DoesNotExist:
        logger.warning("Inquiry %s does not exist; skipping", inquiry_id)
        return

    data = {"inquiry_id": str(inquiry.id), "status": inquiry.status}
    notify_user(
        user=inquiry.tutor.user,
        type=NotificationType.INQUIRY_REQUEST,
        title=_("Inquiry received"),
        body=_("An administrator created an inquiry for you."),
        data=data,
    )
    notify_user(
        user=inquiry.family,
        type=NotificationType.INQUIRY_CREATED,
        title=_("Inquiry created"),
        body=_("An administrator created an inquiry with your tutor."),
        data=data,
    )


@shared_task(bind=True, base=BaseTaskWithRetry)
def notify_inquiry_result(self, inquiryId: str) -> None:
    """
    Notify Provider with iquiry and family user with inquiry results.
    """
    try:
        inquiry = Inquiry.objects.select_related("family", "tutor__user").get(
            id=inquiryId
        )
    except Inquiry.DoesNotExist:
        logger.warning("Inquiry %s does not exist; skipping", inquiryId)
        return

    if inquiry.status in ProviderResponse:
        ntype = NotificationType.INQUIRY_RESPONSE
        title = _("Inquiry answered")
        body = _("Tutor has responded to your inquiry")
        user = inquiry.family

    elif inquiry.status == InquiryStatus.PENDING:
        ntype = NotificationType.INQUIRY_REQUEST
        title = _("Inquiry recieved")
        body = _("You have recieved inquiry")
        user = inquiry.tutor.user
    elif inquiry.status == InquiryStatus.CANCELLED:
        ntype = NotificationType.INQUIRY_CANCELED
        title = _("Inquiry canceled")
        body = _("Client has cancelled their inquiry")
        user = inquiry.tutor.user
    else:
        return

    notify_user(
        user=user,
        type=ntype,
        title=title,
        body=body,
        data={
            "inquiry_id": str(inquiry.id),
            "status": inquiry.status,
        },
    )


@shared_task(bind=True, base=BaseTaskWithRetry)
def notify_review_result(self, listingId: str, comment: str = None) -> None:
    """
    Notify Masterclass Provider that their listing application was approved or rejected.
    """
    try:
        listing = Listing.objects.select_related("owner").get(id=listingId)
    except Listing.DoesNotExist:
        logger.warning("Listing %s does not exist; skipping", listingId)
        return

    if listing.owner is None:
        logger.warning("Listing %s has no owner; skipping notification", listingId)
        return

    if listing.status == ListingStatus.ACTIVE:
        ntype = NotificationType.LISTING_APPROVED
        title = _("Listing approved")
        body = _("Your listing application has been approved.")
    elif listing.status == ListingStatus.REJECTED:
        ntype = NotificationType.LISTING_REJECTED
        title = _("Listing Rejected")
        body = _("Your listing application has been rejected.")

        if comment:
            body = f"{body} {comment}"
    else:
        return

    notify_user(
        listing.owner,
        type=ntype,
        title=title,
        body=body,
        data={
            "listing_id": str(listing.id),
            "status": listing.status,
        },
    )


@shared_task(bind=True, base=BaseTaskWithRetry)
def notify_verification_result(self, verification_id: int) -> None:
    """
    Notify a provider that their application was approved or rejected.
    """
    try:
        verification = ProviderVerification.objects.select_related("user").get(
            id=verification_id
        )
    except ProviderVerification.DoesNotExist:
        logger.warning("Verification %s no longer exists; skipping.", verification_id)
        return

    provider = verification.get_provider_type_display()

    if verification.status == StatusChoices.APPROVED:
        ntype = NotificationType.PROVIDER_APPROVED
        title = _("Application approved")
        body = _("Your %(provider)s application has been approved.") % {
            "provider": provider
        }
    elif verification.status == StatusChoices.REJECTED:
        ntype = NotificationType.PROVIDER_REJECTED
        title = _("Application rejected")
        body = _("Your %(provider)s application was rejected.") % {"provider": provider}
        if verification.comment:
            body = f"{body} {verification.comment}"
    else:
        return

    notify_user(
        verification.user,
        type=ntype,
        title=title,
        body=body,
        data={
            "verification_id": verification.id,
            "provider_type": verification.provider_type,
            "status": verification.status,
        },
    )


@shared_task(bind=True, base=BaseTaskWithRetry)
def notify_ownership_result(self, request_id: int) -> None:
    """Notify a provider that their listing ownership request was decided."""
    try:
        ownership = ListingOwnershipRequest.objects.select_related("user", "listing").get(
            id=request_id
        )
    except ListingOwnershipRequest.DoesNotExist:
        logger.warning("Ownership request %s no longer exists; skipping.", request_id)
        return

    title_of = ownership.listing.title
    if ownership.status == StatusChoices.APPROVED:
        ntype = NotificationType.OWNERSHIP_APPROVED
        title = _("Ownership approved")
        body = _("You are now the owner of %(listing)s.") % {"listing": title_of}
    elif ownership.status == StatusChoices.REJECTED:
        ntype = NotificationType.OWNERSHIP_REJECTED
        title = _("Ownership rejected")
        body = _("Your ownership request for %(listing)s was rejected.") % {
            "listing": title_of
        }
        if ownership.comment:
            body = f"{body} {ownership.comment}"
    else:
        return

    notify_user(
        ownership.user,
        type=ntype,
        title=title,
        body=body,
        data={
            "ownership_request_id": ownership.id,
            "listing_id": str(ownership.listing_id),
            "status": ownership.status,
        },
    )
