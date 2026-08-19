import logging

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.providers.ai_screening import screen_cv_pdf
from apps.providers.models import AIScreeningStatus, ProviderVerificationAIScreening

logger = logging.getLogger(__name__)


@shared_task
def screen_provider_cv(screening_id: int) -> None:
    screening = ProviderVerificationAIScreening.objects.select_related(
        "verification"
    ).get(pk=screening_id)
    if screening.status != AIScreeningStatus.QUEUED:
        return

    screening.status = AIScreeningStatus.PROCESSING
    screening.started_at = timezone.now()
    screening.model = settings.OPENAI_CV_MODEL
    screening.save(update_fields=["status", "started_at", "model"])

    try:
        with screening.verification.cv.open("rb") as cv_file:
            pdf_bytes = cv_file.read()
        result = screen_cv_pdf(
            pdf_bytes,
            screening.verification.cv.name.rsplit("/", 1)[-1],
        )
        screening.status = result.recommendation
        screening.summary = result.summary
        screening.strengths = result.strengths
        screening.concerns = result.concerns
        screening.missing_information = result.missing_information
        screening.manual_checks = result.manual_checks
        screening.criteria = result.criteria
        screening.confidence = result.confidence
    except Exception as exc:
        logger.exception("AI CV screening %s failed", screening_id)
        screening.status = AIScreeningStatus.FAILED
        screening.error_message = str(exc)[:2000]
    finally:
        screening.completed_at = timezone.now()
        screening.save()


def queue_cv_screening(verification) -> ProviderVerificationAIScreening | None:
    if not settings.AI_CV_SCREENING_ENABLED or not verification.cv:
        return None
    screening = ProviderVerificationAIScreening.objects.create(
        verification=verification,
        model=settings.OPENAI_CV_MODEL,
    )
    screen_provider_cv.delay(screening.pk)
    return screening
