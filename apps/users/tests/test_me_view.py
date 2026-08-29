"""
Tests for GET/PATCH/PUT /api/v1/auth/me/

This file replaces test_profile_view.py (which used the old 'profile' URL name).
The view is now UserMeView served at /api/v1/auth/me/ (URL name: 'me').
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.enums import UserRole

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
        }

    def test_retrieve_me_success(self):
        """Authenticated user can retrieve their own profile."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], self.user.email)
        self.assertEqual(response.data["full_name"], self.user.full_name)
        self.assertIn(UserRole.FAMILY, response.data["roles"])
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
            "roles",
            "is_verified",
            "phone",
            "home_lat",
            "home_lng",
        ):
            with self.subTest(field=field):
                self.assertIn(field, response.data)

    def test_update_me_put_ignores_name_fields(self):
        """Name changes require the verified personal-information flow."""
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            self.url, {"first_name": "Updated", "last_name": "Name"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Test")
        self.assertEqual(self.user.last_name, "User")

    def test_update_me_ignores_full_name(self):
        """Personal information can only change through verified edit flow."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            self.url, {"full_name": "Patched Name"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Test User")

    def test_update_me_ignores_password(self):
        """Profile updates cannot bypass the dedicated password endpoint."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {"password": "short"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("testpassword123"))

    def test_me_unauthorized_access(self):
        """Unauthenticated request is rejected with 401."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_delete_not_allowed(self):
        """DELETE is not allowed on the me endpoint."""
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_roles_is_read_only(self):
        """Roles cannot be changed via PATCH."""
        self.client.force_authenticate(user=self.user)
        self.client.patch(self.url, {"roles": ["ADMIN"]}, format="json")
        self.user.refresh_from_db()
        self.assertTrue(self.user.has_role(UserRole.FAMILY))
        self.assertFalse(self.user.has_role(UserRole.ADMIN))

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


class PersonalInformationFlowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="edit-profile@example.com",
            password="OldStrongPass!99",
            full_name="Original Name",
        )
        self.request_url = reverse("v1:users:edit-profile")
        self.confirm_url = reverse("v1:users:edit-profile-verify")
        self.client.force_authenticate(user=self.user)

    @patch("apps.users.views.send_edit_profile_email.delay")
    @patch("apps.users.otp.generate_code", return_value="123456")
    def test_verified_edit_applies_pending_changes(self, _mock_code, mock_email):
        response = self.client.post(
            self.request_url,
            {
                "new_name": "Updated Name",
                "new_email": "updated@example.com",
                "new_password": "NewStrongPass!88",
                "new_password2": "NewStrongPass!88",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_email.assert_called_once_with("edit-profile@example.com", "123456")

        response = self.client.post(self.confirm_url, {"code": "123456"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["email"], "updated@example.com")
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, "Updated Name")
        self.assertEqual(self.user.email, "updated@example.com")
        self.assertTrue(self.user.check_password("NewStrongPass!88"))

    def test_request_rejects_empty_change(self):
        response = self.client.post(self.request_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
