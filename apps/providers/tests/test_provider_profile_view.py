import uuid

from knox.models import AuthToken
from rest_framework.test import APIClient, APITestCase

from apps.providers.models import ProviderProfile
from apps.users.enums import UserRole
from apps.users.models import CustomUser

PROFILE_URL = "/api/v1/provider/profile/"


def make_user(
    role: str = UserRole.FAMILY,
    verified: bool = True,
    email: str | None = None,
) -> CustomUser:
    email = email or f"{role.lower()}_{uuid.uuid4().hex[:8]}@example.com"
    return CustomUser.objects.create_user(
        email=email,
        password="TestPass123!",
        role=role,
        is_verified=verified,
    )


def auth_client(user: CustomUser) -> APIClient:
    client = APIClient()
    _, token = AuthToken.objects.create(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


class ProviderProfileGetTests(APITestCase):
    def test_tutor_can_get_profile(self):
        user = make_user(role=UserRole.TUTOR)
        client = auth_client(user)
        resp = client.get(PROFILE_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["role"], UserRole.TUTOR)
        self.assertEqual(resp.data["email"], user.email)
        self.assertTrue(resp.data["is_verified"])

    def test_masterclass_can_get_profile(self):
        user = make_user(role=UserRole.MASTERCLASS)
        client = auth_client(user)
        resp = client.get(PROFILE_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["role"], UserRole.MASTERCLASS)

    def test_profile_auto_created_on_first_get(self):
        user = make_user(role=UserRole.TUTOR)
        self.assertFalse(ProviderProfile.objects.filter(user=user).exists())
        client = auth_client(user)
        resp = client.get(PROFILE_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(ProviderProfile.objects.filter(user=user).exists())

    def test_family_get_returns_403(self):
        user = make_user(role=UserRole.FAMILY)
        client = auth_client(user)
        resp = client.get(PROFILE_URL)
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_get_returns_401(self):
        client = APIClient()
        resp = client.get(PROFILE_URL)
        self.assertEqual(resp.status_code, 401)

    def test_unverified_tutor_can_get(self):
        """Profile editing is not gated on is_verified."""
        user = make_user(role=UserRole.TUTOR, verified=False)
        client = auth_client(user)
        resp = client.get(PROFILE_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["is_verified"])


class ProviderProfilePatchTests(APITestCase):
    def test_tutor_patch_display_name_bio_subjects(self):
        user = make_user(role=UserRole.TUTOR)
        client = auth_client(user)
        payload = {
            "display_name": "Ahmed Tutoring",
            "bio": "Expert in secondary maths.",
            "subjects": ["Math", "Arabic"],
            "hourly_rate_qar": 120,
        }
        resp = client.patch(PROFILE_URL, payload, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["display_name"], "Ahmed Tutoring")
        self.assertEqual(resp.data["bio"], "Expert in secondary maths.")
        self.assertEqual(resp.data["subjects"], ["Math", "Arabic"])
        self.assertEqual(resp.data["hourly_rate_qar"], 120)

    def test_patch_is_verified_is_ignored(self):
        """is_verified is read-only; any value in the body must be ignored."""
        user = make_user(role=UserRole.TUTOR, verified=False)
        client = auth_client(user)
        resp = client.patch(PROFILE_URL, {"is_verified": True}, format="json")
        # Request should succeed (200) but is_verified must not change
        self.assertEqual(resp.status_code, 200)
        user.refresh_from_db()
        self.assertFalse(user.is_verified)
        self.assertFalse(resp.data["is_verified"])

    def test_put_returns_405(self):
        user = make_user(role=UserRole.TUTOR)
        client = auth_client(user)
        resp = client.put(PROFILE_URL, {"display_name": "X"}, format="json")
        self.assertEqual(resp.status_code, 405)

    def test_family_patch_returns_403(self):
        user = make_user(role=UserRole.FAMILY)
        client = auth_client(user)
        resp = client.patch(PROFILE_URL, {"display_name": "X"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_patch_returns_401(self):
        client = APIClient()
        resp = client.patch(PROFILE_URL, {"display_name": "X"}, format="json")
        self.assertEqual(resp.status_code, 401)

    def test_unverified_tutor_can_patch(self):
        user = make_user(role=UserRole.TUTOR, verified=False)
        client = auth_client(user)
        resp = client.patch(PROFILE_URL, {"display_name": "Draft Tutor"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["display_name"], "Draft Tutor")

    def test_response_shape_contains_required_fields(self):
        user = make_user(role=UserRole.TUTOR)
        client = auth_client(user)
        resp = client.get(PROFILE_URL)
        self.assertEqual(resp.status_code, 200)
        for field in [
            "user_id",
            "email",
            "full_name",
            "role",
            "is_verified",
            "display_name",
            "bio",
            "subjects",
            "hourly_rate_qar",
            "availability",
            "created_at",
            "updated_at",
        ]:
            self.assertIn(field, resp.data, f"Missing field: {field}")
