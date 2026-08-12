import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import gettext as _

from apps.core.tasks import BaseTaskWithRetry

logger = logging.getLogger(__name__)


@shared_task(bind=True, base=BaseTaskWithRetry)
def send_verification_email(self, email: str, code: str) -> None:
    """Email a registration verification code. Retries on SMTP failure via
    BaseTaskWithRetry (fail_silently=False lets the exception propagate)."""
    subject = _("Your Sabil Life verification code")
    body = _("Your verification code is %(code)s. It expires in 10 minutes.") % {
        "code": code
    }
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )
    logger.info("Verification code sent to %s", email)


@shared_task(bind=True, base=BaseTaskWithRetry)
def send_password_reset_email(self, email: str, code: str) -> None:
    """
    Send a password-reset verification code.

    SMTP errors propagate so BaseTaskWithRetry can retry delivery.
    """
    subject = _("Your Sabil Life password reset code")
    body = _(
        "Your password reset code is %(code)s. "
        "It expires in 10 minutes. "
        "If you did not request a password reset, ignore this email."
    ) % {"code": code}

    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )
    logger.info("Password reset email sent.")
