"""
Tests for the notify_verification_result Celery task.

Verifies the correct in-app Notification is written for each terminal outcome
and that non-terminal states / missing records are no-ops. Push is disabled in
test settings, so these assert on the persisted feed row only.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.notifications.models import Notification, NotificationType
from apps.notifications.tasks import notify_verification_result
from apps.providers.models import ProviderChoices, ProviderVerification, StatusChoices
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.TUTOR):
    return User.objects.create_user(email=email, password="pass1234!", role=role)


class NotifyVerificationResultTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user("tutor@test.com")

    def _verification(self, status, comment=""):
        return ProviderVerification.objects.create(
            user=self.user,
            provider_type=ProviderChoices.TUTOR,
            status=status,
            comment=comment,
        )

    def test_approved_creates_notification(self):
        v = self._verification(StatusChoices.APPROVED)
        notify_verification_result(v.id)

        note = Notification.objects.get(user=self.user)
        self.assertEqual(note.type, NotificationType.PROVIDER_APPROVED)
        self.assertIn("approved", note.body.lower())
        self.assertEqual(note.data["verification_id"], v.id)
        self.assertEqual(note.data["status"], StatusChoices.APPROVED)

    def test_rejected_includes_reviewer_comment(self):
        v = self._verification(StatusChoices.REJECTED, comment="Missing documents.")
        notify_verification_result(v.id)

        note = Notification.objects.get(user=self.user)
        self.assertEqual(note.type, NotificationType.PROVIDER_REJECTED)
        self.assertIn("Missing documents.", note.body)

    def test_non_terminal_status_is_noop(self):
        v = self._verification(StatusChoices.PENDING)
        notify_verification_result(v.id)
        self.assertFalse(Notification.objects.exists())

    def test_missing_verification_is_noop(self):
        # Should not raise even though the id does not exist.
        notify_verification_result(999999)
        self.assertFalse(Notification.objects.exists())

    def test_push_is_attempted_for_terminal_outcome(self):
        v = self._verification(StatusChoices.APPROVED)
        with patch("apps.notifications.services.send_push_to_user") as mock_push:
            notify_verification_result(v.id)
        mock_push.assert_called_once()
