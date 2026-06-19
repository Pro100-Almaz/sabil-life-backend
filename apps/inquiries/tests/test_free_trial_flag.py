"""
Tests for the BILLING_GATE_ENABLED free-trial flag in inquiry services.

Verifies that:
- When BILLING_GATE_ENABLED=False (default), accepting an inquiry flips
  contact_revealed=True on the inquiry row.
- When BILLING_GATE_ENABLED=True, accepting an inquiry leaves
  contact_revealed=False.
- Other transitions (CONTACTED, DECLINED, COMPLETED) never touch
  contact_revealed regardless of the flag.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.inquiries.models import Inquiry, InquiryStatus
from apps.inquiries.services import transition
from apps.users.enums import UserRole

User = get_user_model()


def _make_user(email, role):
    return User.objects.create_user(email=email, password="pass1234!", role=role)


def _make_inquiry(status_val=InquiryStatus.NEW):
    uid = id(object())
    family = _make_user(f"fam_ft_{uid}@test.com", UserRole.FAMILY)
    tutor = _make_user(f"tut_ft_{uid}@test.com", UserRole.TUTOR)
    listing = Listing.objects.create(
        title="FT Listing",
        category=ListingCategory.TUTORING,
        status=ListingStatus.ACTIVE,
        owner=tutor,
    )
    return Inquiry.objects.create(
        family=family,
        listing=listing,
        provider=tutor,
        message="Test",
        status=status_val,
        contact_revealed=False,
    )


@pytest.mark.django_db
class TestFreeTrialFlag:
    """Unit tests for the BILLING_GATE_ENABLED stopgap."""

    @override_settings(BILLING_GATE_ENABLED=False)
    def test_accept_flips_contact_revealed_when_gate_disabled(self):
        """Free-trial mode: accepting an inquiry reveals contact immediately."""
        inq = _make_inquiry(InquiryStatus.NEW)
        result = transition(inq, InquiryStatus.ACCEPTED, actor=inq.provider)
        result.refresh_from_db()
        assert result.contact_revealed is True

    @override_settings(BILLING_GATE_ENABLED=True)
    def test_accept_leaves_contact_hidden_when_gate_enabled(self):
        """Billing-gate mode: accepting an inquiry does NOT reveal contact."""
        inq = _make_inquiry(InquiryStatus.NEW)
        result = transition(inq, InquiryStatus.ACCEPTED, actor=inq.provider)
        result.refresh_from_db()
        assert result.contact_revealed is False

    @override_settings(BILLING_GATE_ENABLED=False)
    def test_contacted_does_not_flip_contact_revealed(self):
        """CONTACTED transition never changes contact_revealed."""
        inq = _make_inquiry(InquiryStatus.NEW)
        result = transition(inq, InquiryStatus.CONTACTED, actor=inq.provider)
        result.refresh_from_db()
        assert result.contact_revealed is False

    @override_settings(BILLING_GATE_ENABLED=False)
    def test_declined_does_not_flip_contact_revealed(self):
        """DECLINED transition never changes contact_revealed."""
        inq = _make_inquiry(InquiryStatus.NEW)
        result = transition(inq, InquiryStatus.DECLINED, actor=inq.provider)
        result.refresh_from_db()
        assert result.contact_revealed is False

    @override_settings(BILLING_GATE_ENABLED=False)
    def test_completed_does_not_change_contact_revealed(self):
        """COMPLETED transition does not change contact_revealed."""
        inq = _make_inquiry(InquiryStatus.ACCEPTED)
        # Pre-set contact_revealed=True (as it would be after free-trial accept)
        inq.contact_revealed = True
        inq.save(update_fields=["contact_revealed", "updated_at"])

        result = transition(inq, InquiryStatus.COMPLETED, actor=inq.provider)
        result.refresh_from_db()
        # contact_revealed stays True — completing doesn't retract it
        assert result.contact_revealed is True

    @override_settings(BILLING_GATE_ENABLED=False)
    def test_contact_revealed_persisted_in_db(self):
        """The contact_revealed flip is persisted (not just in-memory)."""
        inq = _make_inquiry(InquiryStatus.NEW)
        transition(inq, InquiryStatus.ACCEPTED, actor=inq.provider)
        # Fetch a fresh copy from DB
        fresh = Inquiry.objects.get(pk=inq.pk)
        assert fresh.contact_revealed is True
