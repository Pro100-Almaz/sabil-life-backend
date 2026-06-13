"""
Tests for POST /api/v1/auth/register/

Covers:
- FAMILY registration: succeeds, is_verified=True, returns Knox token
- TUTOR registration: succeeds, is_verified=False
- MASTERCLASS registration: succeeds, is_verified=False
- ADMIN role rejected with 400
- Weak / duplicate / missing-field validations
- Response shape: {user, token, expiry}
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import UserRole

User = get_user_model()


class RegisterViewTests(APITestCase):
    """Test suite for POST /api/v1/auth/register/"""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("v1:users:register")

    def _family_data(self, email="family@example.com"):
        return {
            "email": email,
            "password": "StrongPass!99",
            "full_name": "Sara Al-Kuwari",
            "role": "FAMILY",
            "phone": "+97455512345",
        }

    # ------------------------------------------------------------------
    # Happy paths
    # ------------------------------------------------------------------

    def test_register_family_success(self):
        """FAMILY registration returns 201 with Knox token and user data."""
        response = self.client.post(self.url, self._family_data(), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Response shape
        self.assertIn("token", response.data)
        self.assertIn("expiry", response.data)
        self.assertIn("user", response.data)

        user_data = response.data["user"]
        self.assertEqual(user_data["email"], "family@example.com")
        self.assertEqual(user_data["role"], UserRole.FAMILY)
        self.assertEqual(user_data["full_name"], "Sara Al-Kuwari")

    def test_register_family_is_verified_true(self):
        """FAMILY users are auto-verified on registration."""
        response = self.client.post(
            self.url, self._family_data("family_v@example.com"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["user"]["is_verified"])

        user = User.objects.get(email="family_v@example.com")
        self.assertTrue(user.is_verified)

    def test_register_tutor_success(self):
        """TUTOR registration succeeds and is_verified defaults to False."""
        data = {
            "email": "tutor@example.com",
            "password": "StrongPass!99",
            "full_name": "Ahmed Al-Thani",
            "role": "TUTOR",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["role"], UserRole.TUTOR)
        self.assertFalse(response.data["user"]["is_verified"])

        user = User.objects.get(email="tutor@example.com")
        self.assertFalse(user.is_verified)
        self.assertTrue(user.is_provider)

    def test_register_masterclass_success(self):
        """MASTERCLASS registration succeeds and is_verified defaults to False."""
        data = {
            "email": "masterclass@example.com",
            "password": "StrongPass!99",
            "full_name": "Noor Al-Dosari",
            "role": "MASTERCLASS",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data["user"]["is_verified"])

        user = User.objects.get(email="masterclass@example.com")
        self.assertTrue(user.is_provider)

    def test_register_default_role_is_family(self):
        """Omitting role defaults to FAMILY."""
        data = {
            "email": "norole@example.com",
            "password": "StrongPass!99",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["role"], UserRole.FAMILY)

    def test_register_token_works_on_me_endpoint(self):
        """Token returned by register is immediately usable on /me/."""
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
        """full_name and phone are optional; registration succeeds without them."""
        data = {"email": "minimal@example.com", "password": "StrongPass!99"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # ------------------------------------------------------------------
    # Role restriction
    # ------------------------------------------------------------------

    def test_register_admin_role_rejected(self):
        """Public register with role=ADMIN must be rejected with 400."""
        data = {
            "email": "wantadmin@example.com",
            "password": "StrongPass!99",
            "role": "ADMIN",
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("role", response.data)

    # ------------------------------------------------------------------
    # Password validation
    # ------------------------------------------------------------------

    def test_register_weak_password_too_short(self):
        """Password shorter than MIN_PASSWORD_LENGTH is rejected."""
        data = {"email": "short@example.com", "password": "short"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_common_password_rejected(self):
        """Common password is rejected by Django's CommonPasswordValidator."""
        data = {"email": "common@example.com", "password": "password"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_numeric_password_rejected(self):
        """All-numeric password is rejected."""
        data = {"email": "numeric@example.com", "password": "12345678"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    # ------------------------------------------------------------------
    # Duplicate / missing fields
    # ------------------------------------------------------------------

    def test_register_duplicate_email_rejected(self):
        """Registering with an already-used email returns 400."""
        self.client.post(self.url, self._family_data("dup@example.com"), format="json")
        response = self.client.post(
            self.url, self._family_data("dup@example.com"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_missing_email(self):
        """Missing email returns 400 with email field error."""
        data = {"password": "StrongPass!99"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_missing_password(self):
        """Missing password returns 400 with password field error."""
        data = {"email": "nopw@example.com"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_register_invalid_email_format(self):
        """Invalid email format returns 400."""
        data = {"email": "not-an-email", "password": "StrongPass!99"}
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    # ------------------------------------------------------------------
    # No auth required
    # ------------------------------------------------------------------

    def test_register_does_not_require_auth(self):
        """Register endpoint is public — no credentials needed."""
        # No force_authenticate, no credentials set
        response = self.client.post(
            self.url, self._family_data("public@example.com"), format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_register_get_not_allowed(self):
        """GET on register endpoint returns 405."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
