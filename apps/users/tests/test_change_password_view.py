from unittest.mock import patch

from django.urls import reverse
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import CustomUser


class ChangePasswordViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("v1:users:change-password")
        self.user = CustomUser.objects.create_user(
            email="change-password@example.com",
            password="OldStrongPass!99",
            is_active=True,
        )
        _, token = AuthToken.objects.create(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    @patch("apps.users.views.send_password_changed_email.delay")
    def test_changes_password_revokes_tokens_and_sends_email(self, mock_email):
        AuthToken.objects.create(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                self.url,
                {
                    "old_password": "OldStrongPass!99",
                    "new_password": "NewStrongPass!88",
                    "new_password2": "NewStrongPass!88",
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPass!88"))
        self.assertFalse(AuthToken.objects.filter(user=self.user).exists())
        mock_email.assert_called_once_with(self.user.email)

    def test_rejects_incorrect_old_password(self):
        response = self.client.post(
            self.url,
            {
                "old_password": "WrongPassword!99",
                "new_password": "NewStrongPass!88",
                "new_password2": "NewStrongPass!88",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("old_password", response.data)

    def test_rejects_mismatched_passwords(self):
        response = self.client.post(
            self.url,
            {
                "old_password": "OldStrongPass!99",
                "new_password": "NewStrongPass!88",
                "new_password2": "DifferentPass!88",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password2", response.data)

    def test_rejects_weak_password(self):
        response = self.client.post(
            self.url,
            {
                "old_password": "OldStrongPass!99",
                "new_password": "password",
                "new_password2": "password",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.data)

    def test_rejects_reusing_current_password(self):
        response = self.client.post(
            self.url,
            {
                "old_password": "OldStrongPass!99",
                "new_password": "OldStrongPass!99",
                "new_password2": "OldStrongPass!99",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.data)

    def test_requires_authentication(self):
        self.client.credentials()
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
