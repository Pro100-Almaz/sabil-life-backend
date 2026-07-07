"""
Tests for the notification API endpoints:
  POST /api/v1/notifications/devices/            — register/upsert FCM token
  POST /api/v1/notifications/devices/unregister/ — deactivate token
  GET  /api/v1/notifications/                     — own feed
  GET  /api/v1/notifications/unread-count/        — badge count
  POST /api/v1/notifications/{id}/read/           — mark one read
  POST /api/v1/notifications/read-all/            — mark all read
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.notifications.models import Device, Notification, NotificationType, Platform
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.TUTOR):
    return User.objects.create_user(email=email, password="pass1234!", role=role)


class DeviceApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user("tutor@test.com")
        cls.register_url = reverse("v1:notifications:devices-list")
        cls.unregister_url = reverse("v1:notifications:devices-unregister")

    def test_register_creates_device(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post(
            self.register_url, {"fcm_token": "abc", "platform": Platform.ANDROID}
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Device.objects.filter(user=self.user, is_active=True).count(), 1)

    def test_register_is_idempotent_upsert(self):
        self.client.force_authenticate(self.user)
        payload = {"fcm_token": "abc", "platform": Platform.ANDROID}
        self.client.post(self.register_url, payload)
        self.client.post(self.register_url, payload)
        self.assertEqual(Device.objects.filter(fcm_token="abc").count(), 1)

    def test_token_rebinds_to_new_user(self):
        other = make_user("other@test.com")
        Device.objects.create(user=other, fcm_token="abc", platform=Platform.IOS)
        self.client.force_authenticate(self.user)
        self.client.post(
            self.register_url, {"fcm_token": "abc", "platform": Platform.ANDROID}
        )
        device = Device.objects.get(fcm_token="abc")
        self.assertEqual(device.user, self.user)

    def test_unregister_deactivates(self):
        Device.objects.create(user=self.user, fcm_token="abc", platform=Platform.IOS)
        self.client.force_authenticate(self.user)
        resp = self.client.post(self.unregister_url, {"fcm_token": "abc"})
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Device.objects.get(fcm_token="abc").is_active)

    def test_anonymous_cannot_register(self):
        resp = self.client.post(
            self.register_url, {"fcm_token": "abc", "platform": Platform.ANDROID}
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class NotificationFeedApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = make_user("tutor@test.com")
        cls.other = make_user("other@test.com")
        cls.list_url = reverse("v1:notifications:notifications-list")
        cls.unread_url = reverse("v1:notifications:notifications-unread-count")
        cls.read_all_url = reverse("v1:notifications:notifications-read-all")

    def _make_note(self, user, is_read=False):
        return Notification.objects.create(
            user=user,
            type=NotificationType.PROVIDER_APPROVED,
            title="Approved",
            body="Body",
            is_read=is_read,
        )

    def _read_url(self, note_id):
        return reverse(
            "v1:notifications:notifications-read", kwargs={"id": note_id}
        )

    def test_feed_lists_only_own_notifications(self):
        self._make_note(self.user)
        self._make_note(self.other)
        self.client.force_authenticate(self.user)
        resp = self.client.get(self.list_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)

    def test_unread_count(self):
        self._make_note(self.user, is_read=False)
        self._make_note(self.user, is_read=True)
        self.client.force_authenticate(self.user)
        resp = self.client.get(self.unread_url)
        self.assertEqual(resp.data["unread"], 1)

    def test_mark_one_read(self):
        note = self._make_note(self.user)
        self.client.force_authenticate(self.user)
        resp = self.client.post(self._read_url(note.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        note.refresh_from_db()
        self.assertTrue(note.is_read)
        self.assertIsNotNone(note.read_at)

    def test_cannot_mark_others_notification_read(self):
        note = self._make_note(self.other)
        self.client.force_authenticate(self.user)
        resp = self.client.post(self._read_url(note.id))
        # Scoped queryset → nothing updated.
        self.assertEqual(resp.data["updated"], 0)
        note.refresh_from_db()
        self.assertFalse(note.is_read)

    def test_read_all(self):
        self._make_note(self.user)
        self._make_note(self.user)
        self.client.force_authenticate(self.user)
        resp = self.client.post(self.read_all_url)
        self.assertEqual(resp.data["updated"], 2)
        self.assertEqual(
            Notification.objects.filter(user=self.user, is_read=False).count(), 0
        )
