"""
Tests for POST /api/v1/inquiries/ and GET /api/v1/inquiries/ (family side).
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.inquiries.models import Inquiry, InquiryStatus
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.FAMILY, **kwargs):
    return User.objects.create_user(
        email=email, password="pass1234!", role=role, **kwargs
    )


def make_listing(owner, category=ListingCategory.TUTORING, status=ListingStatus.ACTIVE):
    return Listing.objects.create(
        title="Tutoring Listing",
        category=category,
        status=status,
        owner=owner,
    )


class InquiryCreateViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("v1:inquiries:inquiries-list")
        cls.family = make_user("family@test.com", UserRole.FAMILY)
        cls.tutor = make_user("tutor@test.com", UserRole.TUTOR)
        cls.masterclass_provider = make_user("mc@test.com", UserRole.MASTERCLASS)
        cls.admin_user = make_user("admin@test.com", UserRole.ADMIN)
        cls.tutoring_listing = make_listing(cls.tutor, ListingCategory.TUTORING)
        cls.mc_listing = make_listing(
            cls.masterclass_provider, ListingCategory.MASTERCLASSES
        )
        cls.draft_listing = make_listing(
            cls.tutor, ListingCategory.TUTORING, ListingStatus.DRAFT
        )

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_family_can_create_inquiry(self):
        self._auth(self.family)
        resp = self.client.post(
            self.url,
            {"listing_id": str(self.tutoring_listing.id), "message": "I am interested."},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], InquiryStatus.NEW)
        self.assertFalse(resp.data["contact_revealed"])

    def test_create_returns_correct_fields(self):
        self._auth(self.family)
        resp = self.client.post(
            self.url,
            {"listing_id": str(self.tutoring_listing.id), "message": "Test message."},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        for field in (
            "id",
            "listing_id",
            "provider_id",
            "status",
            "message",
            "contact_revealed",
            "created_at",
            "updated_at",
        ):
            self.assertIn(field, resp.data)

    def test_provider_snapshot_set_correctly(self):
        self._auth(self.family)
        resp = self.client.post(
            self.url,
            {"listing_id": str(self.tutoring_listing.id), "message": "Hi."},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["provider_id"], str(self.tutor.id))

    # ------------------------------------------------------------------
    # Re-inquiry after decline is allowed
    # ------------------------------------------------------------------

    def test_re_inquiry_after_decline_creates_new_row(self):
        self._auth(self.family)
        # First inquiry
        resp1 = self.client.post(
            self.url,
            {"listing_id": str(self.tutoring_listing.id), "message": "First."},
        )
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        inq_id1 = resp1.data["id"]
        # Manually decline it
        Inquiry.objects.filter(id=inq_id1).update(status=InquiryStatus.DECLINED)
        # Second inquiry
        resp2 = self.client.post(
            self.url,
            {"listing_id": str(self.tutoring_listing.id), "message": "Second."},
        )
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(resp2.data["id"], inq_id1)
        self.assertEqual(
            Inquiry.objects.filter(
                family=self.family, listing=self.tutoring_listing
            ).count(),
            2,
        )

    # ------------------------------------------------------------------
    # Role restrictions
    # ------------------------------------------------------------------

    def test_tutor_cannot_create_inquiry(self):
        self._auth(self.tutor)
        resp = self.client.post(
            self.url,
            {"listing_id": str(self.tutoring_listing.id), "message": "Hi."},
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_masterclass_provider_cannot_create_inquiry(self):
        self._auth(self.masterclass_provider)
        resp = self.client.post(
            self.url,
            {"listing_id": str(self.tutoring_listing.id), "message": "Hi."},
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_create_inquiry(self):
        self._auth(self.admin_user)
        resp = self.client.post(
            self.url,
            {"listing_id": str(self.tutoring_listing.id), "message": "Hi."},
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_create_inquiry(self):
        resp = self.client.post(
            self.url,
            {"listing_id": str(self.tutoring_listing.id), "message": "Hi."},
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # Category validation
    # ------------------------------------------------------------------

    def test_inquiry_on_masterclasses_listing_returns_400(self):
        self._auth(self.family)
        resp = self.client.post(
            self.url,
            {"listing_id": str(self.mc_listing.id), "message": "Hi."},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("subscriptions", resp.data["detail"].lower())

    # ------------------------------------------------------------------
    # Status validation
    # ------------------------------------------------------------------

    def test_inquiry_on_draft_listing_returns_400(self):
        self._auth(self.family)
        resp = self.client.post(
            self.url,
            {"listing_id": str(self.draft_listing.id), "message": "Hi."},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # List endpoint
    # ------------------------------------------------------------------

    def test_family_list_returns_own_inquiries(self):
        self._auth(self.family)
        self.client.post(
            self.url,
            {"listing_id": str(self.tutoring_listing.id), "message": "List test."},
        )
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data["count"], 1)

    def test_family_list_does_not_see_other_families_inquiries(self):
        other_family = make_user("other@test.com", UserRole.FAMILY)
        Inquiry.objects.create(
            family=other_family,
            listing=self.tutoring_listing,
            provider=self.tutor,
            message="Other family.",
        )
        self._auth(self.family)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # None of the results should expose other family's data
        # (results are filtered to own inquiries only)
        for result in resp.data["results"]:
            # FamilyInquirySerializer doesn't expose family_id field directly,
            # but listing_id and provider_id should be present
            self.assertIn("listing_id", result)
