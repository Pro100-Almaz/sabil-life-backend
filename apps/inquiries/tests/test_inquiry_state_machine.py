"""
Tests for the inquiry state machine (services.transition).

Covers every valid transition and every invalid transition (expects 409 or
InvalidTransition exception).
"""

import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.inquiries.models import Inquiry, InquiryStatus
from apps.inquiries.services import InvalidTransition, transition
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.FAMILY):
    return User.objects.create_user(email=email, password="pass1234!", role=role)


def make_inquiry(status_val=InquiryStatus.NEW):
    family = make_user(f"fam_{status_val}_{id(object())}@test.com", UserRole.FAMILY)
    tutor = make_user(f"tut_{status_val}_{id(object())}@test.com", UserRole.TUTOR)
    listing = Listing.objects.create(
        title="Listing",
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
    )


@pytest.mark.django_db
class TestInquiryStateMachine:
    """Test every valid and invalid transition in the state machine."""

    # ------------------------------------------------------------------
    # Valid transitions
    # ------------------------------------------------------------------

    def test_new_to_contacted(self):
        inq = make_inquiry(InquiryStatus.NEW)
        result = transition(inq, InquiryStatus.CONTACTED, actor=inq.provider)
        assert result.status == InquiryStatus.CONTACTED

    def test_new_to_accepted(self):
        inq = make_inquiry(InquiryStatus.NEW)
        result = transition(inq, InquiryStatus.ACCEPTED, actor=inq.provider)
        assert result.status == InquiryStatus.ACCEPTED

    def test_new_to_declined(self):
        inq = make_inquiry(InquiryStatus.NEW)
        result = transition(inq, InquiryStatus.DECLINED, actor=inq.provider)
        assert result.status == InquiryStatus.DECLINED

    def test_contacted_to_accepted(self):
        inq = make_inquiry(InquiryStatus.CONTACTED)
        result = transition(inq, InquiryStatus.ACCEPTED, actor=inq.provider)
        assert result.status == InquiryStatus.ACCEPTED

    def test_contacted_to_declined(self):
        inq = make_inquiry(InquiryStatus.CONTACTED)
        result = transition(inq, InquiryStatus.DECLINED, actor=inq.provider)
        assert result.status == InquiryStatus.DECLINED

    def test_accepted_to_completed(self):
        inq = make_inquiry(InquiryStatus.ACCEPTED)
        result = transition(inq, InquiryStatus.COMPLETED, actor=inq.provider)
        assert result.status == InquiryStatus.COMPLETED

    # ------------------------------------------------------------------
    # Invalid transitions — terminal states
    # ------------------------------------------------------------------

    def test_declined_to_completed_raises(self):
        inq = make_inquiry(InquiryStatus.DECLINED)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.COMPLETED, actor=inq.provider)

    def test_declined_to_accepted_raises(self):
        inq = make_inquiry(InquiryStatus.DECLINED)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.ACCEPTED, actor=inq.provider)

    def test_completed_to_accepted_raises(self):
        inq = make_inquiry(InquiryStatus.COMPLETED)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.ACCEPTED, actor=inq.provider)

    def test_completed_to_new_raises(self):
        inq = make_inquiry(InquiryStatus.COMPLETED)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.NEW, actor=inq.provider)

    # ------------------------------------------------------------------
    # Invalid transitions — non-terminal states
    # ------------------------------------------------------------------

    def test_accepted_to_contacted_raises(self):
        inq = make_inquiry(InquiryStatus.ACCEPTED)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.CONTACTED, actor=inq.provider)

    def test_accepted_to_new_raises(self):
        inq = make_inquiry(InquiryStatus.ACCEPTED)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.NEW, actor=inq.provider)

    def test_new_to_completed_raises(self):
        inq = make_inquiry(InquiryStatus.NEW)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.COMPLETED, actor=inq.provider)

    def test_contacted_to_new_raises(self):
        inq = make_inquiry(InquiryStatus.CONTACTED)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.NEW, actor=inq.provider)

    # ------------------------------------------------------------------
    # Transition persists to DB
    # ------------------------------------------------------------------

    def test_transition_saves_to_db(self):
        inq = make_inquiry(InquiryStatus.NEW)
        transition(inq, InquiryStatus.CONTACTED, actor=inq.provider)
        inq.refresh_from_db()
        assert inq.status == InquiryStatus.CONTACTED


@pytest.mark.django_db
class TestProviderTransitionEndpoints:
    """Test the provider transition action endpoints (409 on invalid)."""

    @classmethod
    def setup_method(cls):
        pass

    def _setup(self):
        from rest_framework.test import APIClient

        self.client = APIClient()
        self.family = User.objects.create_user(
            email="fam_ep@test.com", password="pass1234!", role=UserRole.FAMILY
        )
        self.tutor = User.objects.create_user(
            email="tut_ep@test.com", password="pass1234!", role=UserRole.TUTOR
        )
        self.listing = Listing.objects.create(
            title="EP Listing",
            category=ListingCategory.TUTORING,
            status=ListingStatus.ACTIVE,
            owner=self.tutor,
        )

    def _make_inquiry(self, status_val=InquiryStatus.NEW):
        return Inquiry.objects.create(
            family=self.family,
            listing=self.listing,
            provider=self.tutor,
            message="Test",
            status=status_val,
        )

    def _url(self, inq_id, action):
        from django.urls import reverse

        return reverse(
            f"v1:provider-inquiries:provider-inquiries-{action}",
            kwargs={"id": str(inq_id)},
        )

    def test_decline_on_accepted_returns_409(self):
        self._setup()
        inq = self._make_inquiry(InquiryStatus.ACCEPTED)
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.post(self._url(inq.id, "decline"))
        assert resp.status_code == 409

    def test_complete_on_new_returns_409(self):
        self._setup()
        inq = self._make_inquiry(InquiryStatus.NEW)
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.post(self._url(inq.id, "complete"))
        assert resp.status_code == 409

    def test_contacted_on_declined_returns_409(self):
        self._setup()
        inq = self._make_inquiry(InquiryStatus.DECLINED)
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.post(self._url(inq.id, "contacted"))
        assert resp.status_code == 409
