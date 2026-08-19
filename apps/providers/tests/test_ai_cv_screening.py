from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.providers.ai_screening import CVScreeningResult
from apps.providers.models import (
    AIScreeningStatus,
    ProviderChoices,
    ProviderVerification,
    ProviderVerificationAIScreening,
)
from apps.providers.tasks import queue_cv_screening, screen_provider_cv
from apps.users.models import CustomUser


@override_settings(
    AI_CV_SCREENING_ENABLED=True,
    OPENAI_API_KEY="test-key",
    OPENAI_CV_MODEL="test-model",
)
class AIScreeningTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="screening@example.com",
            password="TestPass123!",
        )
        self.verification = ProviderVerification.objects.create(
            user=self.user,
            provider_type=ProviderChoices.MASTERCLASS,
            cv=SimpleUploadedFile(
                "resume.pdf",
                b"%PDF-1.4\n% test PDF",
                content_type="application/pdf",
            ),
        )

    @patch("apps.providers.tasks.screen_provider_cv.delay")
    def test_queue_creates_advisory_screening(self, delay):
        screening = queue_cv_screening(self.verification)

        self.assertIsNotNone(screening)
        self.assertEqual(screening.status, AIScreeningStatus.QUEUED)
        delay.assert_called_once_with(screening.pk)
        self.verification.refresh_from_db()
        self.assertNotEqual(self.verification.status, "APPROVED")

    @patch("apps.providers.tasks.screen_cv_pdf")
    def test_task_persists_structured_result(self, screen_cv_pdf):
        screening = ProviderVerificationAIScreening.objects.create(
            verification=self.verification
        )
        screen_cv_pdf.return_value = CVScreeningResult(
            recommendation=AIScreeningStatus.NEEDS_REVIEW,
            summary="Relevant experience requires manual verification.",
            strengths=["Teaching experience"],
            concerns=["Dates are unclear"],
            missing_information=["References"],
            manual_checks=["Verify certificate"],
            criteria=[{"criterion": "Experience", "assessment": "Present"}],
            confidence=78,
        )

        screen_provider_cv.run(screening.pk)

        screening.refresh_from_db()
        self.assertEqual(screening.status, AIScreeningStatus.NEEDS_REVIEW)
        self.assertEqual(screening.confidence, 78)
        self.assertIsNotNone(screening.completed_at)
        self.verification.refresh_from_db()
        self.assertNotEqual(self.verification.status, "APPROVED")
