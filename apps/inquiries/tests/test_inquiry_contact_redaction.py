"""
Tests for the contact redaction pattern in ProviderInquirySerializer.

Phase 5 (BILLING_GATE_ENABLED=True): family contact fields are always null
regardless of contact_revealed value. The `family` block is always present
with null contact fields so the client shape is stable.

Phase 6 stopgap (BILLING_GATE_ENABLED=False, the default): accepting an
inquiry auto-flips contact_revealed=True and real contact values appear
in the provider response.
"""

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.inquiries.models import Inquiry, InquiryStatus
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.FAMILY, **kw):
    return User.objects.create_user(email=email, password="pass1234!", role=role, **kw)


class InquiryContactRedactionGatedTests(APITestCase):
    """
    Tests with BILLING_GATE_ENABLED=True — contact is always redacted.
    These cover the original Phase 5 behaviour and the production billing path.
    """

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

    @override_settings(BILLING_GATE_ENABLED=True)
    def test_family_block_present_in_provider_response(self):
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("family", resp.data)

    @override_settings(BILLING_GATE_ENABLED=True)
    def test_family_id_is_present_and_non_null(self):
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        family = resp.data["family"]
        self.assertIsNotNone(family["id"])
        self.assertEqual(family["id"], str(self.family.id))

    @override_settings(BILLING_GATE_ENABLED=True)
    def test_full_name_is_null_when_gate_enabled(self):
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        self.assertIsNone(resp.data["family"]["full_name"])

    @override_settings(BILLING_GATE_ENABLED=True)
    def test_phone_is_null_when_gate_enabled(self):
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        self.assertIsNone(resp.data["family"]["phone"])

    @override_settings(BILLING_GATE_ENABLED=True)
    def test_email_is_null_when_gate_enabled(self):
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        self.assertIsNone(resp.data["family"]["email"])

    @override_settings(BILLING_GATE_ENABLED=True)
    def test_contact_still_null_on_accepted_when_gate_enabled(self):
        """
        With billing gate on, even ACCEPTED + contact_revealed=False stays null.
        Phase 6 billing service will flip contact_revealed when payment clears.
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


class InquiryContactRevealFreeTrialTests(APITestCase):
    """
    Tests with BILLING_GATE_ENABLED=False (the default / free-trial mode).

    After a provider accepts an inquiry, contact_revealed flips to True and
    the provider sees the real contact details in their response.
    """

    @classmethod
    def setUpTestData(cls):
        cls.family = make_user(
            "fam_free@test.com",
            UserRole.FAMILY,
            full_name="Nour Al-Fardan",
            phone="+97455599999",
        )
        cls.tutor = make_user("tut_free@test.com", UserRole.TUTOR)
        cls.listing = Listing.objects.create(
            title="Free Trial Listing",
            category=ListingCategory.TUTORING,
            status=ListingStatus.ACTIVE,
            owner=cls.tutor,
        )

    def _accept_url(self, inq_id):
        return reverse(
            "v1:provider-inquiries:provider-inquiries-accept",
            kwargs={"id": str(inq_id)},
        )

    def _detail_url(self, inq_id):
        return reverse(
            "v1:provider-inquiries:provider-inquiries-detail",
            kwargs={"id": str(inq_id)},
        )

    @override_settings(BILLING_GATE_ENABLED=False)
    def test_contact_revealed_after_accept_free_trial(self):
        """
        With free-trial mode, accepting an inquiry should immediately reveal
        the family's real contact data in the provider's response.
        """
        inquiry = Inquiry.objects.create(
            family=self.family,
            listing=self.listing,
            provider=self.tutor,
            message="Please accept",
            status=InquiryStatus.NEW,
        )
        self.client.force_authenticate(user=self.tutor)
        self.client.post(self._accept_url(inquiry.id))

        resp = self.client.get(self._detail_url(inquiry.id))
        self.assertEqual(resp.status_code, 200)
        family = resp.data["family"]
        self.assertEqual(family["full_name"], "Nour Al-Fardan")
        self.assertEqual(family["phone"], "+97455599999")
        self.assertEqual(family["email"], self.family.email)

    @override_settings(BILLING_GATE_ENABLED=False)
    def test_contact_revealed_flag_true_after_accept(self):
        """contact_revealed DB field flips to True after accept in free-trial mode."""
        inquiry = Inquiry.objects.create(
            family=self.family,
            listing=self.listing,
            provider=self.tutor,
            message="Please accept",
            status=InquiryStatus.NEW,
        )
        self.client.force_authenticate(user=self.tutor)
        self.client.post(self._accept_url(inquiry.id))

        inquiry.refresh_from_db()
        self.assertTrue(inquiry.contact_revealed)

    @override_settings(BILLING_GATE_ENABLED=True)
    def test_contact_not_revealed_when_gate_enabled(self):
        """With billing gate on, accepting does NOT flip contact_revealed."""
        inquiry = Inquiry.objects.create(
            family=self.family,
            listing=self.listing,
            provider=self.tutor,
            message="Gate test",
            status=InquiryStatus.NEW,
        )
        self.client.force_authenticate(user=self.tutor)
        self.client.post(self._accept_url(inquiry.id))

        inquiry.refresh_from_db()
        self.assertFalse(inquiry.contact_revealed)

    @override_settings(BILLING_GATE_ENABLED=True)
    def test_contact_still_null_in_response_when_gate_enabled(self):
        """With billing gate on, provider response still shows null contact."""
        inquiry = Inquiry.objects.create(
            family=self.family,
            listing=self.listing,
            provider=self.tutor,
            message="Gate test",
            status=InquiryStatus.NEW,
        )
        self.client.force_authenticate(user=self.tutor)
        self.client.post(self._accept_url(inquiry.id))

        resp = self.client.get(self._detail_url(inquiry.id))
        family = resp.data["family"]
        self.assertIsNone(family["full_name"])
        self.assertIsNone(family["phone"])
        self.assertIsNone(family["email"])
