"""
Tests for the inquiry state machine (services.transition).

Covers every valid transition and every invalid transition (expects 409 or
InvalidTransition exception).
"""

import pytest
from django.contrib.auth import get_user_model

from apps.inquiries.models import Inquiry, InquiryStatus
from apps.inquiries.services import InvalidTransition, transition
from apps.providers.models import TutorDetail
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.FAMILY):
    return User.objects.create_user(email=email, password="pass1234!", role=role)


def make_inquiry(status_val=InquiryStatus.NEW):
    uid = id(object())
    family = make_user(f"fam_{status_val}_{uid}@test.com", UserRole.FAMILY)
    tutor_user = make_user(f"tut_{status_val}_{uid}@test.com", UserRole.TUTOR)
    tutor = TutorDetail.objects.create(user=tutor_user)
    return Inquiry.objects.create(
        family=family,
        tutor=tutor,
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
        result = transition(inq, InquiryStatus.CONTACTED, actor=inq.tutor.user)
        assert result.status == InquiryStatus.CONTACTED

    def test_new_to_accepted(self):
        inq = make_inquiry(InquiryStatus.NEW)
        result = transition(inq, InquiryStatus.ACCEPTED, actor=inq.tutor.user)
        assert result.status == InquiryStatus.ACCEPTED

    def test_new_to_declined(self):
        inq = make_inquiry(InquiryStatus.NEW)
        result = transition(inq, InquiryStatus.DECLINED, actor=inq.tutor.user)
        assert result.status == InquiryStatus.DECLINED

    def test_new_to_cancelled(self):
        inq = make_inquiry(InquiryStatus.NEW)
        result = transition(inq, InquiryStatus.CANCELLED, actor=inq.family)
        assert result.status == InquiryStatus.CANCELLED

    def test_contacted_to_accepted(self):
        inq = make_inquiry(InquiryStatus.CONTACTED)
        result = transition(inq, InquiryStatus.ACCEPTED, actor=inq.tutor.user)
        assert result.status == InquiryStatus.ACCEPTED

    def test_contacted_to_declined(self):
        inq = make_inquiry(InquiryStatus.CONTACTED)
        result = transition(inq, InquiryStatus.DECLINED, actor=inq.tutor.user)
        assert result.status == InquiryStatus.DECLINED

    def test_contacted_to_cancelled(self):
        inq = make_inquiry(InquiryStatus.CONTACTED)
        result = transition(inq, InquiryStatus.CANCELLED, actor=inq.family)
        assert result.status == InquiryStatus.CANCELLED

    def test_accepted_to_completed(self):
        inq = make_inquiry(InquiryStatus.ACCEPTED)
        result = transition(inq, InquiryStatus.COMPLETED, actor=inq.tutor.user)
        assert result.status == InquiryStatus.COMPLETED

    # ------------------------------------------------------------------
    # Invalid transitions — terminal states
    # ------------------------------------------------------------------

    def test_declined_to_completed_raises(self):
        inq = make_inquiry(InquiryStatus.DECLINED)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.COMPLETED, actor=inq.tutor.user)

    def test_declined_to_accepted_raises(self):
        inq = make_inquiry(InquiryStatus.DECLINED)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.ACCEPTED, actor=inq.tutor.user)

    def test_completed_to_accepted_raises(self):
        inq = make_inquiry(InquiryStatus.COMPLETED)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.ACCEPTED, actor=inq.tutor.user)

    def test_completed_to_new_raises(self):
        inq = make_inquiry(InquiryStatus.COMPLETED)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.NEW, actor=inq.tutor.user)

    def test_cancelled_to_accepted_raises(self):
        inq = make_inquiry(InquiryStatus.CANCELLED)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.ACCEPTED, actor=inq.tutor.user)

    # ------------------------------------------------------------------
    # Invalid transitions — non-terminal states
    # ------------------------------------------------------------------

    def test_accepted_to_contacted_raises(self):
        inq = make_inquiry(InquiryStatus.ACCEPTED)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.CONTACTED, actor=inq.tutor.user)

    def test_accepted_to_cancelled_raises(self):
        inq = make_inquiry(InquiryStatus.ACCEPTED)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.CANCELLED, actor=inq.family)

    def test_accepted_to_new_raises(self):
        inq = make_inquiry(InquiryStatus.ACCEPTED)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.NEW, actor=inq.tutor.user)

    def test_new_to_completed_raises(self):
        inq = make_inquiry(InquiryStatus.NEW)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.COMPLETED, actor=inq.tutor.user)

    def test_contacted_to_new_raises(self):
        inq = make_inquiry(InquiryStatus.CONTACTED)
        with pytest.raises(InvalidTransition):
            transition(inq, InquiryStatus.NEW, actor=inq.tutor.user)

    # ------------------------------------------------------------------
    # Transition persists to DB
    # ------------------------------------------------------------------

    def test_transition_saves_to_db(self):
        inq = make_inquiry(InquiryStatus.NEW)
        transition(inq, InquiryStatus.CONTACTED, actor=inq.tutor.user)
        inq.refresh_from_db()
        assert inq.status == InquiryStatus.CONTACTED


@pytest.mark.django_db
class TestTutorStatusUpdateEndpoint:
    """Test the tutor PATCH status endpoint (409 on invalid transitions)."""

    def _setup(self):
        from rest_framework.test import APIClient

        self.client = APIClient()
        self.family = User.objects.create_user(
            email="fam_ep@test.com", password="pass1234!", role=UserRole.FAMILY
        )
        tutor_user = User.objects.create_user(
            email="tut_ep@test.com", password="pass1234!", role=UserRole.TUTOR
        )
        self.tutor = TutorDetail.objects.create(user=tutor_user)

    def _make_inquiry(self, status_val=InquiryStatus.NEW):
        return Inquiry.objects.create(
            family=self.family,
            tutor=self.tutor,
            message="Test",
            status=status_val,
        )

    def _url(self, inq_id):
        from django.urls import reverse

        return reverse(
            "v1:tutor-inquiries:tutor-inquiries-detail",
            kwargs={"id": str(inq_id)},
        )

    def test_decline_on_accepted_returns_409(self):
        self._setup()
        inq = self._make_inquiry(InquiryStatus.ACCEPTED)
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.patch(self._url(inq.id), {"status": InquiryStatus.DECLINED})
        assert resp.status_code == 409

    def test_complete_on_new_returns_409(self):
        self._setup()
        inq = self._make_inquiry(InquiryStatus.NEW)
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.patch(self._url(inq.id), {"status": InquiryStatus.COMPLETED})
        assert resp.status_code == 409

    def test_contacted_on_declined_returns_409(self):
        self._setup()
        inq = self._make_inquiry(InquiryStatus.DECLINED)
        self.client.force_authenticate(user=self.tutor.user)
        resp = self.client.patch(self._url(inq.id), {"status": InquiryStatus.CONTACTED})
        assert resp.status_code == 409
