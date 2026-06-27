"""
Tests for tutor-side inquiry endpoints.

Covers:
- Only the addressed tutor sees the inquiry; other tutors get empty list/404.
- Status filtering.
- PATCH status update for each valid transition.
- FAMILY cannot access tutor endpoints.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.inquiries.models import Inquiry, InquiryStatus
from apps.providers.models import TutorDetail
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.FAMILY, **kw):
    return User.objects.create_user(email=email, password="pass1234!", role=role, **kw)


def make_tutor_detail(email):
    user = make_user(email, UserRole.TUTOR)
    return TutorDetail.objects.create(user=user)


def make_inquiry(family, tutor, inq_status=InquiryStatus.NEW):
    return Inquiry.objects.create(
        family=family,
        tutor=tutor,
        message="Test inquiry",
        status=inq_status,
    )


class TutorInquiryViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.family = make_user("fam@prov.com", UserRole.FAMILY)
        cls.tutor = make_tutor_detail("tutor@prov.com")
        cls.other_tutor = make_tutor_detail("other_tutor@prov.com")
        cls.inquiry = make_inquiry(cls.family, cls.tutor)

    def _list_url(self):
        return reverse("v1:tutor-inquiries:tutor-inquiries-list")

    def _detail_url(self, inq_id):
        return reverse(
            "v1:tutor-inquiries:tutor-inquiries-detail",
            kwargs={"id": str(inq_id)},
        )

    # ------------------------------------------------------------------
    # List isolation
    # ------------------------------------------------------------------

    def test_tutor_sees_own_inquiries(self):
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.get(self._list_url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in resp.data["results"]]
        self.assertIn(str(self.inquiry.id), ids)

    def test_other_tutor_sees_empty_list(self):
        self.client.force_authenticate(user=self.other_tutor.user)
        resp = self.client.get(self._list_url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 0)

    def test_status_filter_works(self):
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.get(self._list_url(), {"status": "NEW"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for r in resp.data["results"]:
            self.assertEqual(r["status"], "NEW")

    def test_status_filter_excludes_non_matching(self):
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.get(self._list_url(), {"status": "ACCEPTED"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 0)

    # ------------------------------------------------------------------
    # Detail isolation
    # ------------------------------------------------------------------

    def test_tutor_can_retrieve_own_inquiry(self):
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["id"], str(self.inquiry.id))

    def test_other_tutor_gets_404_on_detail(self):
        self.client.force_authenticate(user=self.other_tutor.user)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------
    # Status update (PATCH)
    # ------------------------------------------------------------------

    def test_update_to_contacted(self):
        inq = make_inquiry(self.family, self.tutor, InquiryStatus.NEW)
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.patch(
            self._detail_url(inq.id), {"status": InquiryStatus.CONTACTED}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], InquiryStatus.CONTACTED)

    def test_update_to_accepted(self):
        inq = make_inquiry(self.family, self.tutor, InquiryStatus.NEW)
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.patch(
            self._detail_url(inq.id), {"status": InquiryStatus.ACCEPTED}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], InquiryStatus.ACCEPTED)

    def test_update_to_declined(self):
        inq = make_inquiry(self.family, self.tutor, InquiryStatus.NEW)
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.patch(
            self._detail_url(inq.id), {"status": InquiryStatus.DECLINED}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], InquiryStatus.DECLINED)

    def test_update_to_completed(self):
        inq = make_inquiry(self.family, self.tutor, InquiryStatus.ACCEPTED)
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.patch(
            self._detail_url(inq.id), {"status": InquiryStatus.COMPLETED}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], InquiryStatus.COMPLETED)

    def test_invalid_transition_returns_409(self):
        inq = make_inquiry(self.family, self.tutor, InquiryStatus.NEW)
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.patch(
            self._detail_url(inq.id), {"status": InquiryStatus.COMPLETED}
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_tutor_cannot_set_cancelled_status(self):
        """CANCELLED is family-only and not a valid choice for the tutor."""
        inq = make_inquiry(self.family, self.tutor, InquiryStatus.NEW)
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.patch(
            self._detail_url(inq.id), {"status": InquiryStatus.CANCELLED}
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tutor_cannot_update_other_tutors_inquiry(self):
        self.client.force_authenticate(user=self.other_tutor.user)
        resp = self.client.patch(
            self._detail_url(self.inquiry.id), {"status": InquiryStatus.CONTACTED}
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------
    # Role restrictions
    # ------------------------------------------------------------------

    def test_family_cannot_access_tutor_endpoints(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.get(self._list_url())
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
