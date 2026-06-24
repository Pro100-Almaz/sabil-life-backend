import uuid

from knox.models import AuthToken
from rest_framework.test import APIClient, APITestCase

from apps.providers.models import TutorDetail
from apps.users.enums import UserRole
from apps.users.models import CustomUser

TUTOR_DETAIL_URL = "/api/v1/provider/tutor-detail/"


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


class TutorDetailSoftDeleteTests(APITestCase):
    def setUp(self):
        self.user = make_user(role=UserRole.TUTOR)
        self.client = auth_client(self.user)
        self.client.post(TUTOR_DETAIL_URL, {"bio": "Hello"}, format="json")

    def test_soft_delete_returns_204(self):
        resp = self.client.delete(TUTOR_DETAIL_URL)
        self.assertEqual(resp.status_code, 204)

    def test_soft_delete_sets_deleted_at(self):
        self.client.delete(TUTOR_DETAIL_URL)
        detail = TutorDetail.objects.get(user=self.user)
        self.assertIsNotNone(detail.deleted_at)

    def test_soft_delete_removes_tutor_role(self):
        self.assertTrue(self.user.has_role(UserRole.TUTOR))
        self.client.delete(TUTOR_DETAIL_URL)
        self.user.refresh_from_db()
        if hasattr(self.user, "_role_names_cache"):
            del self.user._role_names_cache
        self.assertFalse(self.user.has_role(UserRole.TUTOR))

    def test_soft_delete_preserves_row_in_db(self):
        self.client.delete(TUTOR_DETAIL_URL)
        self.assertTrue(TutorDetail.objects.filter(user=self.user).exists())

    def test_get_after_soft_delete_returns_404(self):
        self.client.delete(TUTOR_DETAIL_URL)
        resp = self.client.get(TUTOR_DETAIL_URL)
        self.assertEqual(resp.status_code, 404)

    def test_second_delete_returns_404(self):
        self.client.delete(TUTOR_DETAIL_URL)
        resp = self.client.delete(TUTOR_DETAIL_URL)
        self.assertEqual(resp.status_code, 404)

    def test_anonymous_delete_returns_401(self):
        client = APIClient()
        resp = client.delete(TUTOR_DETAIL_URL)
        self.assertEqual(resp.status_code, 401)

    def test_delete_without_detail_returns_404(self):
        # Any authenticated user may reach the endpoint (the TUTOR role is
        # only granted on verification approval), but with no tutor detail
        # of their own they get a 404, not a 403.
        family = make_user(role=UserRole.FAMILY)
        client = auth_client(family)
        resp = client.delete(TUTOR_DETAIL_URL)
        self.assertEqual(resp.status_code, 404)
