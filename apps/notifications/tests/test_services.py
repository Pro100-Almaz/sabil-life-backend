"""
Tests for the notification service layer.

FCM is mocked — no network. Focus is on: the feed row is always written, the
multicast is only built when there are active tokens, and tokens FCM reports as
unregistered are deactivated.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.notifications.models import Device, Notification, NotificationType, Platform
from apps.notifications import services
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.TUTOR):
    return User.objects.create_user(email=email, password="pass1234!", role=role)


class NotifyUserTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user("tutor@test.com")

    @override_settings(PUSH_NOTIFICATIONS_ENABLED=False)
    def test_feed_row_written_when_push_disabled(self):
        note = services.notify_user(
            self.user,
            type=NotificationType.PROVIDER_APPROVED,
            title="Approved",
            body="Your application was approved.",
            data={"verification_id": 1},
        )
        self.assertIsInstance(note, Notification)
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)

    @override_settings(PUSH_NOTIFICATIONS_ENABLED=False)
    def test_no_fcm_call_when_push_disabled(self):
        Device.objects.create(
            user=self.user, fcm_token="tok", platform=Platform.ANDROID
        )
        fake_messaging = MagicMock()
        with patch("firebase_admin.messaging", fake_messaging, create=True):
            services.send_push_to_user(self.user, "t", "b", {})
        fake_messaging.send_each_for_multicast.assert_not_called()


@override_settings(PUSH_NOTIFICATIONS_ENABLED=True)
class SendPushTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user("tutor@test.com")

    def setUp(self):
        # Insertion order matters — the service preserves it in the token list.
        Device.objects.create(
            user=self.user, fcm_token="good-token", platform=Platform.ANDROID
        )
        Device.objects.create(
            user=self.user, fcm_token="dead-token", platform=Platform.IOS
        )

    def _fake_messaging(self, responses):
        fake = MagicMock()
        fake.UnregisteredError = type("UnregisteredError", (Exception,), {})
        fake.send_each_for_multicast.return_value = SimpleNamespace(responses=responses)
        return fake

    def test_dead_token_is_deactivated(self):
        fake = self._fake_messaging([])  # placeholder, replaced below
        fake.send_each_for_multicast.return_value = SimpleNamespace(
            responses=[
                SimpleNamespace(success=True, exception=None),
                SimpleNamespace(
                    success=False, exception=fake.UnregisteredError("gone")
                ),
            ]
        )
        with patch.object(services, "_get_firebase_app", return_value=object()), patch(
            "firebase_admin.messaging", fake, create=True
        ):
            services.send_push_to_user(self.user, "t", "b", {"k": 1})

        self.assertTrue(Device.objects.get(fcm_token="good-token").is_active)
        self.assertFalse(Device.objects.get(fcm_token="dead-token").is_active)

    def test_all_tokens_sent(self):
        fake = self._fake_messaging(
            [
                SimpleNamespace(success=True, exception=None),
                SimpleNamespace(success=True, exception=None),
            ]
        )
        with patch.object(services, "_get_firebase_app", return_value=object()), patch(
            "firebase_admin.messaging", fake, create=True
        ):
            services.send_push_to_user(self.user, "t", "b", {"k": 1})
        fake.send_each_for_multicast.assert_called_once()

    def test_no_active_devices_skips_send(self):
        Device.objects.filter(user=self.user).update(is_active=False)
        fake = MagicMock()
        with patch.object(services, "_get_firebase_app", return_value=object()), patch(
            "firebase_admin.messaging", fake, create=True
        ):
            services.send_push_to_user(self.user, "t", "b", {})
        fake.send_each_for_multicast.assert_not_called()
