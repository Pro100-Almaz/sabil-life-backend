"""
Tests for the contact redaction pattern in TutorInquirySerializer.

With BILLING_GATE_ENABLED=True: family contact fields are always null
regardless of contact_revealed value. The `family` block is always present
with null contact fields so the client shape is stable.

Phase 6 stopgap (BILLING_GATE_ENABLED=False, the default): accepting an
inquiry auto-flips contact_revealed=True and real contact values appear
in the tutor response.
"""

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
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


class InquiryContactRedactionGatedTests(APITestCase):
    """
    Tests with BILLING_GATE_ENABLED=True — contact is always redacted.
    """

    @classmethod
    def setUpTestData(cls):
        cls.family = make_user(
            "fam_redact@test.com",
            UserRole.FAMILY,
            full_name="Sara Al-Kuwari",
            phone="+97455512345",
        )
        cls.tutor = make_tutor_detail("tut_redact@test.com")
        cls.inquiry = Inquiry.objects.create(
            family=cls.family,
            tutor=cls.tutor,
            message="Test",
            status=InquiryStatus.NEW,
        )
        cls.inquiry_accepted = Inquiry.objects.create(
            family=cls.family,
            tutor=cls.tutor,
            message="Accepted inquiry",
            status=InquiryStatus.ACCEPTED,
            contact_revealed=False,
        )

    def _detail_url(self, inq_id):
        return reverse(
            "v1:tutor-inquiries:tutor-inquiries-detail",
            kwargs={"id": str(inq_id)},
        )

    @override_settings(BILLING_GATE_ENABLED=True)
    def test_family_block_present_in_tutor_response(self):
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("family", resp.data)

    @override_settings(BILLING_GATE_ENABLED=True)
    def test_family_id_is_present_and_non_null(self):
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        family = resp.data["family"]
        self.assertIsNotNone(family["id"])
        self.assertEqual(family["id"], str(self.family.id))

    @override_settings(BILLING_GATE_ENABLED=True)
    def test_full_name_is_null_when_gate_enabled(self):
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        self.assertIsNone(resp.data["family"]["full_name"])

    @override_settings(BILLING_GATE_ENABLED=True)
    def test_phone_is_null_when_gate_enabled(self):
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        self.assertIsNone(resp.data["family"]["phone"])

    @override_settings(BILLING_GATE_ENABLED=True)
    def test_email_is_null_when_gate_enabled(self):
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.get(self._detail_url(self.inquiry.id))
        self.assertIsNone(resp.data["family"]["email"])

    @override_settings(BILLING_GATE_ENABLED=True)
    def test_contact_still_null_on_accepted_when_gate_enabled(self):
        self.client.force_authenticate(user=self.tutor.user)
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
        self.assertNotIn("family", resp.data)


class InquiryContactRevealFreeTrialTests(APITestCase):
    """
    Tests with BILLING_GATE_ENABLED=False (the default / free-trial mode).

    After a tutor accepts an inquiry, contact_revealed flips to True and
    the tutor sees the real contact details in their response.
    """

    @classmethod
    def setUpTestData(cls):
        cls.family = make_user(
            "fam_free@test.com",
            UserRole.FAMILY,
            full_name="Nour Al-Fardan",
            phone="+97455599999",
        )
        cls.tutor = make_tutor_detail("tut_free@test.com")

    def _status_url(self, inq_id):
        return reverse(
            "v1:tutor-inquiries:tutor-inquiries-detail",
            kwargs={"id": str(inq_id)},
        )

    def _accept(self, inq_id):
        return self.client.patch(
            self._status_url(inq_id), {"status": InquiryStatus.ACCEPTED}
        )

    @override_settings(BILLING_GATE_ENABLED=False)
    def test_contact_revealed_after_accept_free_trial(self):
        inquiry = Inquiry.objects.create(
            family=self.family,
            tutor=self.tutor,
            message="Please accept",
            status=InquiryStatus.NEW,
        )
        self.client.force_authenticate(user=self.tutor.user)
        resp = self._accept(inquiry.id)
        self.assertEqual(resp.status_code, 200)
        family = resp.data["family"]
        self.assertEqual(family["full_name"], "Nour Al-Fardan")
        self.assertEqual(family["phone"], "+97455599999")
        self.assertEqual(family["email"], self.family.email)

    @override_settings(BILLING_GATE_ENABLED=False)
    def test_contact_revealed_flag_true_after_accept(self):
        inquiry = Inquiry.objects.create(
            family=self.family,
            tutor=self.tutor,
            message="Please accept",
            status=InquiryStatus.NEW,
        )
        self.client.force_authenticate(user=self.tutor.user)
        self._accept(inquiry.id)
        inquiry.refresh_from_db()
        self.assertTrue(inquiry.contact_revealed)

    @override_settings(BILLING_GATE_ENABLED=True)
    def test_contact_not_revealed_when_gate_enabled(self):
        inquiry = Inquiry.objects.create(
            family=self.family,
            tutor=self.tutor,
            message="Gate test",
            status=InquiryStatus.NEW,
        )
        self.client.force_authenticate(user=self.tutor.user)
        self._accept(inquiry.id)
        inquiry.refresh_from_db()
        self.assertFalse(inquiry.contact_revealed)

    @override_settings(BILLING_GATE_ENABLED=True)
    def test_contact_still_null_in_response_when_gate_enabled(self):
        inquiry = Inquiry.objects.create(
            family=self.family,
            tutor=self.tutor,
            message="Gate test",
            status=InquiryStatus.NEW,
        )
        self.client.force_authenticate(user=self.tutor.user)
        resp = self._accept(inquiry.id)
        family = resp.data["family"]
        self.assertIsNone(family["full_name"])
        self.assertIsNone(family["phone"])
        self.assertIsNone(family["email"])
