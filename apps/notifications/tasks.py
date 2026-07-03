import logging

from celery import shared_task
from django.utils.translation import gettext as _

from apps.core.tasks import BaseTaskWithRetry
from apps.notifications.models import NotificationType
from apps.notifications.services import notify_user
from apps.providers.models import ProviderVerification, StatusChoices

logger = logging.getLogger(__name__)


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
