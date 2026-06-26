"""
Tests for the family-side inquiry endpoints:
  POST /api/v1/inquiries/             — create
  GET  /api/v1/inquiries/             — list own
  POST /api/v1/inquiries/{id}/cancel/ — cancel own
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.inquiries.models import Inquiry, InquiryStatus
from apps.providers.models import TutorDetail
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.FAMILY, **kwargs):
    return User.objects.create_user(
        email=email, password="pass1234!", role=role, **kwargs
    )


def make_tutor_detail(email, **kwargs):
    user = make_user(email, UserRole.TUTOR)
    return TutorDetail.objects.create(user=user, **kwargs)


class InquiryCreateViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("v1:inquiries:inquiries-list")
        cls.family = make_user("family@test.com", UserRole.FAMILY)
        cls.masterclass_provider = make_user("mc@test.com", UserRole.MASTERCLASS)
        cls.admin_user = make_user("admin@test.com", UserRole.ADMIN)
        cls.tutor = make_tutor_detail("tutor@test.com")
        cls.deleted_tutor = make_tutor_detail("deleted@test.com")
        from django.utils import timezone

        cls.deleted_tutor.deleted_at = timezone.now()
        cls.deleted_tutor.save(update_fields=["deleted_at"])

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def _cancel_url(self, inq_id):
        return reverse("v1:inquiries:inquiries-cancel", kwargs={"id": str(inq_id)})

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_family_can_create_inquiry(self):
        self._auth(self.family)
        resp = self.client.post(
            self.url,
            {"tutor_id": self.tutor.id, "message": "I am interested."},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], InquiryStatus.NEW)
        self.assertFalse(resp.data["contact_revealed"])

    def test_create_returns_correct_fields(self):
        self._auth(self.family)
        resp = self.client.post(
            self.url,
            {"tutor_id": self.tutor.id, "message": "Test message."},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        for field in (
            "id",
            "tutor_id",
            "tutor",
            "status",
            "message",
            "contact_revealed",
            "created_at",
            "updated_at",
        ):
            self.assertIn(field, resp.data)

    def test_tutor_id_set_correctly(self):
        self._auth(self.family)
        resp = self.client.post(
            self.url,
            {"tutor_id": self.tutor.id, "message": "Hi."},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["tutor_id"], self.tutor.id)

    # ------------------------------------------------------------------
    # Re-inquiry after decline is allowed
    # ------------------------------------------------------------------

    def test_re_inquiry_after_decline_creates_new_row(self):
        self._auth(self.family)
        resp1 = self.client.post(
            self.url,
            {"tutor_id": self.tutor.id, "message": "First."},
        )
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        inq_id1 = resp1.data["id"]
        Inquiry.objects.filter(id=inq_id1).update(status=InquiryStatus.DECLINED)
        resp2 = self.client.post(
            self.url,
            {"tutor_id": self.tutor.id, "message": "Second."},
        )
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(resp2.data["id"], inq_id1)
        self.assertEqual(
            Inquiry.objects.filter(family=self.family, tutor=self.tutor).count(),
            2,
        )

    # ------------------------------------------------------------------
    # Role restrictions
    # ------------------------------------------------------------------

    def test_tutor_cannot_create_inquiry(self):
        self._auth(self.tutor.user)
        resp = self.client.post(
            self.url,
            {"tutor_id": self.tutor.id, "message": "Hi."},
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_masterclass_provider_cannot_create_inquiry(self):
        self._auth(self.masterclass_provider)
        resp = self.client.post(
            self.url,
            {"tutor_id": self.tutor.id, "message": "Hi."},
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_create_inquiry(self):
        self._auth(self.admin_user)
        resp = self.client.post(
            self.url,
            {"tutor_id": self.tutor.id, "message": "Hi."},
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_create_inquiry(self):
        resp = self.client.post(
            self.url,
            {"tutor_id": self.tutor.id, "message": "Hi."},
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def test_inquiry_to_unknown_tutor_returns_404(self):
        self._auth(self.family)
        resp = self.client.post(
            self.url,
            {"tutor_id": 999999, "message": "Hi."},
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_inquiry_to_deleted_tutor_returns_400(self):
        self._auth(self.family)
        resp = self.client.post(
            self.url,
            {"tutor_id": self.deleted_tutor.id, "message": "Hi."},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("no longer available", resp.data["detail"].lower())

    # ------------------------------------------------------------------
    # List endpoint
    # ------------------------------------------------------------------

    def test_family_list_returns_own_inquiries(self):
        self._auth(self.family)
        self.client.post(
            self.url,
            {"tutor_id": self.tutor.id, "message": "List test."},
        )
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data["count"], 1)

    def test_family_list_does_not_see_other_families_inquiries(self):
        other_family = make_user("other@test.com", UserRole.FAMILY)
        Inquiry.objects.create(
            family=other_family,
            tutor=self.tutor,
            message="Other family.",
        )
        self._auth(self.family)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 0)

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------

    def test_family_can_cancel_own_inquiry(self):
        inquiry = Inquiry.objects.create(
            family=self.family, tutor=self.tutor, message="Cancel me."
        )
        self._auth(self.family)
        resp = self.client.post(self._cancel_url(inquiry.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], InquiryStatus.CANCELLED)

    def test_cancel_on_completed_returns_409(self):
        inquiry = Inquiry.objects.create(
            family=self.family,
            tutor=self.tutor,
            message="Done.",
            status=InquiryStatus.COMPLETED,
        )
        self._auth(self.family)
        resp = self.client.post(self._cancel_url(inquiry.id))
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_family_cannot_cancel_other_familys_inquiry(self):
        other_family = make_user("other2@test.com", UserRole.FAMILY)
        inquiry = Inquiry.objects.create(
            family=other_family, tutor=self.tutor, message="Not yours."
        )
        self._auth(self.family)
        resp = self.client.post(self._cancel_url(inquiry.id))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
