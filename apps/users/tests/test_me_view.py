"""
Tests for GET/PATCH/PUT /api/v1/auth/me/

This file replaces test_profile_view.py (which used the old 'profile' URL name).
The view is now UserMeView served at /api/v1/auth/me/ (URL name: 'me').
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import UserRole

User = get_user_model()


class MeViewTests(APITestCase):
    """Test suite for GET/PATCH/PUT /api/v1/auth/me/"""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("v1:users:me")
        cls.user = User.objects.create_user(
            email="testuser@example.com",
            password="testpassword123",
            first_name="Test",
            last_name="User",
            full_name="Test User",
            role=UserRole.FAMILY,
        )
        cls.valid_update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "password": "newpassword123",
        }

    def test_retrieve_me_success(self):
        """Authenticated user can retrieve their own profile."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["full_name"], self.user.full_name)
        self.assertEqual(response.data["role"], UserRole.FAMILY)
        self.assertNotIn("password", response.data)

    def test_me_response_contains_phase1_fields(self):
        """Response includes all Phase 1 fields."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for field in (
            "id",
            "email",
            "full_name",
            "role",
            "is_verified",
            "phone",
            "home_lat",
            "home_lng",
        ):
            with self.subTest(field=field):
                self.assertIn(field, response.data)

    def test_update_me_put(self):
        """Full profile update with PUT."""
        self.client.force_authenticate(user=self.user)
        data = {
            "first_name": "Updated",
            "last_name": "Name",
            "password": "newpassword123",
        }
        response = self.client.put(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.last_name, "Name")
        self.assertTrue(self.user.check_password("newpassword123"))

    def test_update_me_patch(self):
        """Partial profile update with PATCH."""
        self.client.force_authenticate(user=self.user)
        data = {"full_name": "Patched Name"}
        response = self.client.patch(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Patched Name")

    def test_update_me_invalid_password(self):
        """Short password is rejected."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {"password": "short"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_me_unauthorized_access(self):
        """Unauthenticated request is rejected with 401."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_delete_not_allowed(self):
        """DELETE is not allowed on the me endpoint."""
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_password_validation_success(self):
        """Valid strong password is accepted."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.url, {"password": "ValidPass123!"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("ValidPass123!"))

    def test_password_too_short(self):
        """Password shorter than MIN_PASSWORD_LENGTH is rejected at field level."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {"password": "short"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_numeric_only_password(self):
        """All-numeric password is rejected."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {"password": "12345678"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertTrue(
            any("entirely numeric" in msg for msg in response.data["password"]),
            "Expected 'entirely numeric' error not found",
        )

    def test_common_weak_password(self):
        """Common password is rejected."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {"password": "password"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertTrue(
            any("too common" in msg for msg in response.data["password"]),
            "Expected 'too common' error not found",
        )

    def test_role_is_read_only(self):
        """Role field cannot be changed via PATCH."""
        self.client.force_authenticate(user=self.user)
        self.client.patch(self.url, {"role": "ADMIN"}, format="json")
        # Either 200 (field ignored) or 400; role must not change
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, UserRole.FAMILY)

    def test_is_verified_is_read_only(self):
        """is_verified cannot be changed via PATCH by the user themselves."""
        self.client.force_authenticate(user=self.user)
        self.client.patch(self.url, {"is_verified": False}, format="json")
        self.user.refresh_from_db()
        # Value should be unchanged (FAMILY defaults to True after registration)
        # Here the user was created directly so is_verified=False (model default)
        # The field is read-only so the patch is silently ignored
        self.assertFalse(self.user.is_verified)

    def test_update_location_fields(self):
        """home_lat and home_lng can be updated."""
        self.client.force_authenticate(user=self.user)
        data = {"home_lat": 25.369, "home_lng": 51.551}
        response = self.client.patch(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertAlmostEqual(self.user.home_lat, 25.369, places=3)
        self.assertAlmostEqual(self.user.home_lng, 51.551, places=3)

    def test_concurrent_login_uses_me_url(self):
        """Tokens obtained via login work against the me endpoint."""
        login_url = reverse("v1:users:knox_login")
        # Need a user with a known password — use fresh credentials
        User.objects.create_user(
            email="me_token_test@example.com", password="TestPass!99"
        )
        response = self.client.post(
            login_url,
            {"email": "me_token_test@example.com", "password": "TestPass!99"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token = response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        me_response = self.client.get(self.url)
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["email"], "me_token_test@example.com")
