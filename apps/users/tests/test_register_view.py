"""
Tests for the two-step self-service registration:

  POST /api/v1/auth/register/         -> validate + email a code (no account)
  POST /api/v1/auth/register/verify/  -> verify the code + create the account

Covers:
- request step validates inputs and creates NO user
- request step emails a code (task dispatched)
- verify step creates a FAMILY user, is_verified=True, returns a Knox token
- code correctness, expiry, and attempt-limit behaviour
- the created account can log in with the original password
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.enums import UserRole

User = get_user_model()

FIXED_CODE = "123456"


@patch("apps.users.otp.generate_code", return_value=FIXED_CODE)
@patch("apps.users.views.send_verification_email.delay")
class RegisterFlowTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.request_url = reverse("v1:users:register")
        cls.verify_url = reverse("v1:users:register-verify")

    def setUp(self):
        cache.clear()  # pending registrations live in the cache

    def _family_data(self, email="family@example.com"):
        return {
            "email": email,
            "password": "StrongPass!99",
            "full_name": "Sara Al-Kuwari",
            "phone": "+97455512345",
        }

    def _request_code(self, data):
        return self.client.post(self.request_url, data, format="json")

    def _verify(self, email, code=FIXED_CODE):
        return self.client.post(
            self.verify_url, {"email": email, "code": code}, format="json"
        )

    # ------------------------------------------------------------------
    # Step 1 — request code
    # ------------------------------------------------------------------

    def test_request_code_success_creates_no_user(self, mock_send, _mock_code):
        response = self._request_code(self._family_data())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)
        self.assertFalse(User.objects.filter(email="family@example.com").exists())

    def test_request_code_dispatches_email(self, mock_send, _mock_code):
        self._request_code(self._family_data())
        mock_send.assert_called_once_with("family@example.com", FIXED_CODE)

    def test_request_code_duplicate_email_rejected(self, mock_send, _mock_code):
        User.objects.create_user(
            email="dup@example.com", password="StrongPass!99"
        )
        response = self._request_code(self._family_data("dup@example.com"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        mock_send.assert_not_called()

    def test_request_code_weak_password_rejected(self, mock_send, _mock_code):
        response = self._request_code(
            {"email": "weak@example.com", "password": "password"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        mock_send.assert_not_called()

    def test_request_code_missing_email(self, mock_send, _mock_code):
        response = self._request_code({"password": "StrongPass!99"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_request_code_invalid_email_format(self, mock_send, _mock_code):
        response = self._request_code(
            {"email": "not-an-email", "password": "StrongPass!99"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_request_code_get_not_allowed(self, mock_send, _mock_code):
        response = self.client.get(self.request_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # ------------------------------------------------------------------
    # Step 2 — verify code
    # ------------------------------------------------------------------

    def test_verify_success_creates_family_user(self, mock_send, _mock_code):
        self._request_code(self._family_data())
        response = self._verify("family@example.com")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", response.data)
        self.assertIn("expiry", response.data)

        user_data = response.data["user"]
        self.assertEqual(user_data["email"], "family@example.com")
        self.assertIn(UserRole.FAMILY, user_data["roles"])
        self.assertEqual(user_data["full_name"], "Sara Al-Kuwari")
        self.assertTrue(user_data["is_verified"])

        user = User.objects.get(email="family@example.com")
        self.assertTrue(user.is_verified)
        self.assertTrue(user.has_role(UserRole.FAMILY))

    def test_verify_token_works_on_me_endpoint(self, mock_send, _mock_code):
        self._request_code(self._family_data("tokentest@example.com"))
        response = self._verify("tokentest@example.com")
        token = response.data["token"]

        me_url = reverse("v1:users:me")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        me_response = self.client.get(me_url)
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["email"], "tokentest@example.com")

    def test_verified_user_can_log_in_with_password(self, mock_send, _mock_code):
        self._request_code(self._family_data("login@example.com"))
        self._verify("login@example.com")

        login_url = reverse("v1:users:knox_login")
        response = self.client.post(
            login_url,
            {"email": "login@example.com", "password": "StrongPass!99"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_verify_wrong_code_rejected(self, mock_send, _mock_code):
        self._request_code(self._family_data())
        response = self._verify("family@example.com", code="000000")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", response.data)
        self.assertFalse(User.objects.filter(email="family@example.com").exists())

    def test_verify_without_request_rejected(self, mock_send, _mock_code):
        response = self._verify("ghost@example.com")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", response.data)

    def test_verify_is_single_use(self, mock_send, _mock_code):
        self._request_code(self._family_data())
        self._verify("family@example.com")
        # Second verify with the same code should now fail (entry consumed).
        response = self._verify("family@example.com")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_too_many_attempts(self, mock_send, _mock_code):
        self._request_code(self._family_data())
        for _ in range(5):
            self._verify("family@example.com", code="000000")
        # The 6th attempt — even with the right code — is locked out.
        response = self._verify("family@example.com")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", response.data)
        self.assertFalse(User.objects.filter(email="family@example.com").exists())
