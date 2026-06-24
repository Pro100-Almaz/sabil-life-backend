"""
Tests for POST /api/v1/auth/register/

Covers:
- Registration always creates FAMILY role
- Returns Knox token
- Weak / duplicate / missing-field validations
- Response shape: {user, token, expiry}
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.enums import UserRole

User = get_user_model()


class RegisterViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("v1:users:register")

    def _family_data(self, email="family@example.com"):
        return {
            "email": email,
            "password": "StrongPass!99",
            "full_name": "Sara Al-Kuwari",
            "phone": "+97455512345",
        }

    # ------------------------------------------------------------------
    # Happy paths
    # ------------------------------------------------------------------

    def test_register_family_success(self):
        response = self.client.post(self.url, self._family_data(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertIn("token", response.data)
        self.assertIn("expiry", response.data)
        self.assertIn("user", response.data)

        user_data = response.data["user"]
        self.assertEqual(user_data["email"], "family@example.com")
        self.assertIn(UserRole.FAMILY, user_data["roles"])
        self.assertEqual(user_data["full_name"], "Sara Al-Kuwari")

    def test_register_is_verified_true(self):
        response = self.client.post(
            self.url, self._family_data("family_v@example.com"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["user"]["is_verified"])

        user = User.objects.get(email="family_v@example.com")
        self.assertTrue(user.is_verified)

    def test_register_gets_family_role(self):
        data = {
            "email": "norole@example.com",
            "password": "StrongPass!99",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(UserRole.FAMILY, response.data["user"]["roles"])

    def test_register_token_works_on_me_endpoint(self):
        response = self.client.post(
            self.url, self._family_data("tokentest@example.com"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        token = response.data["token"]

        me_url = reverse("v1:users:me")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        me_response = self.client.get(me_url)
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["email"], "tokentest@example.com")

    def test_register_optional_fields_omitted(self):
        data = {"email": "minimal@example.com", "password": "StrongPass!99"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_register_role_field_ignored(self):
        """Sending a role field in the request body is silently ignored."""
        data = {
            "email": "wantadmin@example.com",
            "password": "StrongPass!99",
            "role": "ADMIN",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="wantadmin@example.com")
        self.assertTrue(user.has_role(UserRole.FAMILY))
        self.assertFalse(user.has_role(UserRole.ADMIN))

    # ------------------------------------------------------------------
    # Password validation
    # ------------------------------------------------------------------

    def test_register_weak_password_too_short(self):
        data = {"email": "short@example.com", "password": "short"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_common_password_rejected(self):
        data = {"email": "common@example.com", "password": "password"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_numeric_password_rejected(self):
        data = {"email": "numeric@example.com", "password": "12345678"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    # ------------------------------------------------------------------
    # Duplicate / missing fields
    # ------------------------------------------------------------------

    def test_register_duplicate_email_rejected(self):
        self.client.post(self.url, self._family_data("dup@example.com"), format="json")
        response = self.client.post(
            self.url, self._family_data("dup@example.com"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_missing_email(self):
        data = {"password": "StrongPass!99"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_missing_password(self):
        data = {"email": "nopw@example.com"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_invalid_email_format(self):
        data = {"email": "not-an-email", "password": "StrongPass!99"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    # ------------------------------------------------------------------
    # No auth required
    # ------------------------------------------------------------------

    def test_register_does_not_require_auth(self):
        response = self.client.post(
            self.url, self._family_data("public@example.com"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_register_get_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
