import logging

from celery import shared_task
from django.utils.translation import gettext as _

from apps.core.tasks import BaseTaskWithRetry
from apps.notifications.models import NotificationType
from apps.notifications.services import notify_user
from apps.providers.models import ProviderVerification, StatusChoices, TutorDetail
from apps.catalog.models import Listing, ListingStatus
from apps.inquiries.models import Inquiry, InquiryStatus

logger = logging.getLogger(__name__)

ProviderResponse = {
    InquiryStatus.CONTACTED,
    InquiryStatus.ACCEPTED,
    InquiryStatus.DECLINED,
}


@shared_task(bind=True, base=BaseTaskWithRetry)
def notify_inquiry_result(self, inquiryId: str) -> None: 
    """
    Notify Provider with iquiry and family user with inquiry results.
    """
    try:
        inquiry = Inquiry.objects.select_related("user").get(
            id = inquiryId
        )
    except Listing.DoesNotExist:
        logger.warning("Inquiry %s does not exist; skippig", inquiryId)
    
    if inquiry.status in ProviderResponse:
        ntype = NotificationType.INQUIRY_RESPONSE
        title = _("Inquiry answered")
        body = _("Tutor has responded to your inquiry")
        user = inquiry.family
        
    elif inquiry.status == InquiryStatus.NEW:
        ntype = NotificationType.INQUIRY_REQUEST
        title = _("Inquiry recieved")
        body = _("You have recieved inquiry")
        user = inquiry.tutor.user
    elif inquiry.status == InquiryStatus.CANCELLED:
        ntype = NotificationType.INQUIRY_CANCELED
        title = _("Inquiry canceled")
        body = _("Client has cancelled their inquiry")
        user = inquiry.tutor.user
    else: return

    notify_user(
        user=user,
        type=ntype,
        title=title,
        body=body,
        data={
            "inquiry_id": inquiry.id,
            "status": inquiry.status,
        }
    )

@shared_task(bind=True, base=BaseTaskWithRetry)
def notify_review_result(self, listingId: str, comment: str = None) -> None:
    """
    Notify Masterclass Provider that their listing application was approved or rejected.
    """
    try:
        listing = Listing.objects.select_related("owner").get(
            id = listingId
        )
    except Listing.DoesNotExist:
        logger.warning("Listing %s does not exist; skipping", listingId)
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
        body = _("Your %(provider)s application was rejected.") % {
            "provider": provider
        }
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
