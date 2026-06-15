"""
Tests for the Inquiry model — defaults, ordering, __str__, status choices.
"""

import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.inquiries.models import Inquiry, InquiryStatus
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.FAMILY):
    return User.objects.create_user(email=email, password="pass1234!", role=role)


def make_listing(owner, category=ListingCategory.TUTORING, status=ListingStatus.ACTIVE):
    return Listing.objects.create(
        title="Test Listing",
        category=category,
        status=status,
        owner=owner,
    )


def make_inquiry(family, listing, provider, message="Hello"):
    return Inquiry.objects.create(
        family=family,
        listing=listing,
        provider=provider,
        message=message,
    )


@pytest.mark.django_db
class TestInquiryModel:
    def test_default_status_is_new(self):
        family = make_user("family@test.com", UserRole.FAMILY)
        tutor = make_user("tutor@test.com", UserRole.TUTOR)
        listing = make_listing(tutor)
        inquiry = make_inquiry(family, listing, tutor)
        assert inquiry.status == InquiryStatus.NEW

    def test_contact_revealed_defaults_false(self):
        family = make_user("family2@test.com", UserRole.FAMILY)
        tutor = make_user("tutor2@test.com", UserRole.TUTOR)
        listing = make_listing(tutor)
        inquiry = make_inquiry(family, listing, tutor)
        assert inquiry.contact_revealed is False

    def test_str_representation(self):
        family = make_user("family3@test.com", UserRole.FAMILY)
        tutor = make_user("tutor3@test.com", UserRole.TUTOR)
        listing = make_listing(tutor)
        inquiry = make_inquiry(family, listing, tutor)
        assert str(inquiry) == f"Inquiry {inquiry.id} ({inquiry.status})"

    def test_ordering_most_recent_first(self):
        family = make_user("family4@test.com", UserRole.FAMILY)
        tutor = make_user("tutor4@test.com", UserRole.TUTOR)
        listing = make_listing(tutor)
        i1 = make_inquiry(family, listing, tutor, "First")
        i2 = make_inquiry(family, listing, tutor, "Second")
        inquiries = list(Inquiry.objects.filter(family=family))
        assert inquiries[0].id == i2.id
        assert inquiries[1].id == i1.id

    def test_status_choices_contain_expected_values(self):
        choice_values = [c[0] for c in InquiryStatus.choices]
        assert "NEW" in choice_values
        assert "CONTACTED" in choice_values
        assert "ACCEPTED" in choice_values
        assert "DECLINED" in choice_values
        assert "COMPLETED" in choice_values

    def test_uuid_primary_key(self):
        family = make_user("family5@test.com", UserRole.FAMILY)
        tutor = make_user("tutor5@test.com", UserRole.TUTOR)
        listing = make_listing(tutor)
        inquiry = make_inquiry(family, listing, tutor)
        import uuid

        assert isinstance(inquiry.id, uuid.UUID)

    def test_provider_snapshot_is_listing_owner(self):
        family = make_user("family6@test.com", UserRole.FAMILY)
        tutor = make_user("tutor6@test.com", UserRole.TUTOR)
        listing = make_listing(tutor)
        inquiry = make_inquiry(family, listing, tutor)
        assert inquiry.provider_id == tutor.id
