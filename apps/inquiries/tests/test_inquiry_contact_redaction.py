"""
Tests for the contact redaction pattern in ProviderInquirySerializer.

Phase 5: family contact fields (full_name, phone, email) are ALWAYS null
regardless of contact_revealed value. The `family` block is always present
with null contact fields so the client shape is stable across phases.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.inquiries.models import Inquiry, InquiryStatus
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.FAMILY, **kw):
    return User.objects.create_user(email=email, password="pass1234!", role=role, **kw)


class InquiryContactRedactionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.family = make_user(
            "fam_redact@test.com",
            UserRole.FAMILY,
            full_name="Sara Al-Kuwari",
            phone="+97455512345",
        )
        cls.tutor = make_user("tut_redact@test.com", UserRole.TUTOR)
        cls.listing = Listing.objects.create(
            title="Redaction Test Listing",
            category=ListingCategory.TUTORING,
            status=ListingStatus.ACTIVE,
            owner=cls.tutor,
        )
        cls.inquiry = Inquiry.objects.create(
            family=cls.family,
            listing=cls.listing,
            provider=cls.tutor,
            message="Test",
            status=InquiryStatus.NEW,
        )
        cls.inquiry_accepted = Inquiry.objects.create(
            family=cls.family,
            listing=cls.listing,
            provider=cls.tutor,
            message="Accepted inquiry",
            status=InquiryStatus.ACCEPTED,
            contact_revealed=False,
        )

    def _detail_url(self, inq_id):
        return reverse(
            "v1:provider-inquiries:provider-inquiries-detail",
            kwargs={"id": str(inq_id)},
        )

    def test_family_block_present_in_provider_response(self):
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("family", resp.data)

    def test_family_id_is_present_and_non_null(self):
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        family = resp.data["family"]
        self.assertIsNotNone(family["id"])
        self.assertEqual(family["id"], str(self.family.id))

    def test_full_name_is_null_in_phase_5(self):
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        self.assertIsNone(resp.data["family"]["full_name"])

    def test_phone_is_null_in_phase_5(self):
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        self.assertIsNone(resp.data["family"]["phone"])

    def test_email_is_null_in_phase_5(self):
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        self.assertIsNone(resp.data["family"]["email"])

    def test_contact_still_null_even_when_accepted(self):
        """
        Even on an ACCEPTED inquiry (where contact might logically be revealed),
        Phase 5 always nullifies. Phase 6 will flip this.
        """
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.get(self._detail_url(self.inquiry_accepted.id))
        self.assertEqual(resp.status_code, 200)
        family = resp.data["family"]
        self.assertIsNone(family["full_name"])
        self.assertIsNone(family["phone"])
        self.assertIsNone(family["email"])

    def test_family_contact_not_in_family_side_response(self):
        """Family-side response has no nested family block (they view their own data)."""
        self.client.force_authenticate(user=self.family)
        url = reverse(
            "v1:inquiries:inquiries-detail", kwargs={"id": str(self.inquiry.id)}
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        # FamilyInquirySerializer has no "family" key
        self.assertNotIn("family", resp.data)
