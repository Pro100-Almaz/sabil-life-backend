"""
Tests for provider-side inquiry endpoints.

Covers:
- Only the listing's provider sees the inquiry; other tutors get empty list/404.
- MASTERCLASS provider with no inquiries sees empty list.
- All four transition actions accessible by owner.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.inquiries.models import Inquiry, InquiryStatus
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.FAMILY, **kw):
    return User.objects.create_user(email=email, password="pass1234!", role=role, **kw)


def make_listing(
    owner, category=ListingCategory.TUTORING, lst_status=ListingStatus.ACTIVE
):
    return Listing.objects.create(
        title="Test Listing", category=category, status=lst_status, owner=owner
    )


def make_inquiry(family, listing, provider, inq_status=InquiryStatus.NEW):
    return Inquiry.objects.create(
        family=family,
        listing=listing,
        provider=provider,
        message="Test inquiry",
        status=inq_status,
    )


class ProviderInquiryViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.family = make_user("fam@prov.com", UserRole.FAMILY)
        cls.tutor = make_user("tutor@prov.com", UserRole.TUTOR)
        cls.other_tutor = make_user("other_tutor@prov.com", UserRole.TUTOR)
        cls.mc_provider = make_user("mc@prov.com", UserRole.MASTERCLASS)
        cls.listing = make_listing(cls.tutor)
        cls.inquiry = make_inquiry(cls.family, cls.listing, cls.tutor)

    def _list_url(self):
        return reverse("v1:provider-inquiries:provider-inquiries-list")

    def _detail_url(self, inq_id):
        return reverse(
            "v1:provider-inquiries:provider-inquiries-detail",
            kwargs={"id": str(inq_id)},
        )

    def _action_url(self, inq_id, action):
        return reverse(
            f"v1:provider-inquiries:provider-inquiries-{action}",
            kwargs={"id": str(inq_id)},
        )

    # ------------------------------------------------------------------
    # List isolation
    # ------------------------------------------------------------------

    def test_provider_sees_own_inquiries(self):
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.get(self._list_url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in resp.data["results"]]
        self.assertIn(str(self.inquiry.id), ids)

    def test_other_tutor_sees_empty_list(self):
        self.client.force_authenticate(user=self.other_tutor)
        resp = self.client.get(self._list_url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 0)

    def test_masterclass_provider_sees_empty_list(self):
        self.client.force_authenticate(user=self.mc_provider)
        resp = self.client.get(self._list_url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 0)

    def test_status_filter_works(self):
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.get(self._list_url(), {"status": "NEW"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for r in resp.data["results"]:
            self.assertEqual(r["status"], "NEW")

    def test_status_filter_excludes_non_matching(self):
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.get(self._list_url(), {"status": "ACCEPTED"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 0)

    # ------------------------------------------------------------------
    # Detail isolation
    # ------------------------------------------------------------------

    def test_provider_can_retrieve_own_inquiry(self):
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["id"], str(self.inquiry.id))

    def test_other_tutor_gets_404_on_detail(self):
        self.client.force_authenticate(user=self.other_tutor)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------
    # Transition actions
    # ------------------------------------------------------------------

    def test_contacted_action_transitions_to_contacted(self):
        family = make_user("fam_contact@prov.com", UserRole.FAMILY)
        listing = make_listing(self.tutor)
        inq = make_inquiry(family, listing, self.tutor, InquiryStatus.NEW)
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.post(self._action_url(inq.id, "contacted"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], InquiryStatus.CONTACTED)

    def test_accept_action_transitions_to_accepted(self):
        family = make_user("fam_accept@prov.com", UserRole.FAMILY)
        listing = make_listing(self.tutor)
        inq = make_inquiry(family, listing, self.tutor, InquiryStatus.NEW)
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.post(self._action_url(inq.id, "accept"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], InquiryStatus.ACCEPTED)

    def test_decline_action_transitions_to_declined(self):
        family = make_user("fam_decline@prov.com", UserRole.FAMILY)
        listing = make_listing(self.tutor)
        inq = make_inquiry(family, listing, self.tutor, InquiryStatus.NEW)
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.post(self._action_url(inq.id, "decline"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], InquiryStatus.DECLINED)

    def test_complete_action_transitions_to_completed(self):
        family = make_user("fam_complete@prov.com", UserRole.FAMILY)
        listing = make_listing(self.tutor)
        inq = make_inquiry(family, listing, self.tutor, InquiryStatus.ACCEPTED)
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.post(self._action_url(inq.id, "complete"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], InquiryStatus.COMPLETED)

    def test_family_cannot_access_provider_endpoints(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.get(self._list_url())
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
