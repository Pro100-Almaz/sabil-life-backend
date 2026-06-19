"""
Tests for POST /api/v1/listings/{listing_id}/reviews/ — Phase 7.

Covers engagement gate, role gates, auth, rating validation, uniqueness (409).
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.inquiries.models import Inquiry, InquiryStatus
from apps.reviews.models import Review
from apps.subscriptions.models import MasterclassSubscription
from apps.users.enums import UserRole

User = get_user_model()


def _user(email, role=UserRole.FAMILY, **kw):
    return User.objects.create_user(email=email, password="pass1234!", role=role, **kw)


def _listing(category=ListingCategory.TUTORING, owner=None):
    return Listing.objects.create(
        title=f"{category} Listing",
        category=category,
        status=ListingStatus.ACTIVE,
        owner=owner,
    )


def _reviews_url(listing_id):
    return reverse("v1:listing-reviews", kwargs={"listing_id": str(listing_id)})


@pytest.mark.django_db
class TestReviewCreateTutoring:
    """Engagement gate for TUTORING listings."""

    def setup_method(self):
        self.client = APIClient()
        self.tutor = _user("cr_tutor@test.com", UserRole.TUTOR)
        self.listing = _listing(ListingCategory.TUTORING, owner=self.tutor)

    def _make_inquiry(self, family, status_val):
        return Inquiry.objects.create(
            family=family,
            listing=self.listing,
            provider=self.tutor,
            message="Test",
            status=status_val,
        )

    def test_family_with_accepted_inquiry_can_post_201(self):
        family = _user("cr_acc@test.com")
        self._make_inquiry(family, InquiryStatus.ACCEPTED)
        self.client.force_authenticate(user=family)
        resp = self.client.post(
            _reviews_url(self.listing.id), {"rating": 5, "text": "Great!"}
        )
        assert resp.status_code == 201

    def test_family_with_completed_inquiry_can_post_201(self):
        family = _user("cr_comp@test.com")
        self._make_inquiry(family, InquiryStatus.COMPLETED)
        self.client.force_authenticate(user=family)
        resp = self.client.post(
            _reviews_url(self.listing.id), {"rating": 4, "text": "Good."}
        )
        assert resp.status_code == 201

    def test_family_with_new_inquiry_gets_400(self):
        family = _user("cr_new@test.com")
        self._make_inquiry(family, InquiryStatus.NEW)
        self.client.force_authenticate(user=family)
        resp = self.client.post(_reviews_url(self.listing.id), {"rating": 3})
        assert resp.status_code == 400

    def test_family_with_contacted_inquiry_gets_400(self):
        family = _user("cr_contacted@test.com")
        self._make_inquiry(family, InquiryStatus.CONTACTED)
        self.client.force_authenticate(user=family)
        resp = self.client.post(_reviews_url(self.listing.id), {"rating": 3})
        assert resp.status_code == 400

    def test_family_with_declined_inquiry_gets_400(self):
        family = _user("cr_dec@test.com")
        self._make_inquiry(family, InquiryStatus.DECLINED)
        self.client.force_authenticate(user=family)
        resp = self.client.post(_reviews_url(self.listing.id), {"rating": 2})
        assert resp.status_code == 400

    def test_family_with_no_inquiry_gets_400(self):
        family = _user("cr_noinq@test.com")
        self.client.force_authenticate(user=family)
        resp = self.client.post(_reviews_url(self.listing.id), {"rating": 5})
        assert resp.status_code == 400

    def test_engagement_gate_400_message_is_helpful(self):
        family = _user("cr_msg@test.com")
        self.client.force_authenticate(user=family)
        resp = self.client.post(_reviews_url(self.listing.id), {"rating": 5})
        body = resp.json()
        errors = str(body)
        assert "engaged" in errors or "inquiry" in errors or "listing" in errors


@pytest.mark.django_db
class TestReviewCreateMasterclasses:
    """Engagement gate for MASTERCLASSES listings."""

    def setup_method(self):
        self.client = APIClient()
        self.provider = _user("cr_mc_prov@test.com", UserRole.MASTERCLASS)
        self.listing = _listing(ListingCategory.MASTERCLASSES, owner=self.provider)

    def _make_subscription(self, family, status_val="CONFIRMED"):

        s = MasterclassSubscription.objects.create(
            family=family,
            listing=self.listing,
            provider=self.provider,
            status=status_val,
        )
        return s

    def test_family_with_confirmed_subscription_can_post_201(self):
        family = _user("cr_mc_conf@test.com")
        self._make_subscription(family, "CONFIRMED")
        self.client.force_authenticate(user=family)
        resp = self.client.post(
            _reviews_url(self.listing.id), {"rating": 5, "text": "Loved it!"}
        )
        assert resp.status_code == 201

    def test_family_with_cancelled_subscription_can_post_201(self):
        """Cancelled still counts — family attended before cancelling."""
        family = _user("cr_mc_canc@test.com")
        self._make_subscription(family, "CANCELLED")
        self.client.force_authenticate(user=family)
        resp = self.client.post(
            _reviews_url(self.listing.id), {"rating": 4, "text": "Was good."}
        )
        assert resp.status_code == 201

    def test_family_with_no_subscription_gets_400(self):
        family = _user("cr_mc_nosub@test.com")
        self.client.force_authenticate(user=family)
        resp = self.client.post(_reviews_url(self.listing.id), {"rating": 5})
        assert resp.status_code == 400


@pytest.mark.django_db
class TestReviewCreateNoGateCategories:
    """No engagement gate for directory categories."""

    @pytest.mark.parametrize(
        "category",
        [
            ListingCategory.SCHOOLS,
            ListingCategory.NURSERIES,
            ListingCategory.ACTIVITIES,
            ListingCategory.ENTERTAINMENT,
            ListingCategory.PARTNERSHIPS,
        ],
    )
    def test_family_can_review_without_engagement(self, category):
        client = APIClient()
        listing = _listing(category)
        family = _user(f"cr_ng_{category.lower()}@test.com")
        client.force_authenticate(user=family)
        resp = client.post(_reviews_url(listing.id), {"rating": 4, "text": "Nice place!"})
        assert resp.status_code == 201


@pytest.mark.django_db
class TestReviewCreateAuth:
    """Role and auth gates."""

    def setup_method(self):
        self.client = APIClient()
        self.listing = _listing(ListingCategory.SCHOOLS)

    def test_tutor_gets_403(self):
        tutor = _user("cr_tutor_role@test.com", UserRole.TUTOR)
        self.client.force_authenticate(user=tutor)
        resp = self.client.post(_reviews_url(self.listing.id), {"rating": 4})
        assert resp.status_code == 403

    def test_masterclass_gets_403(self):
        mc = _user("cr_mc_role@test.com", UserRole.MASTERCLASS)
        self.client.force_authenticate(user=mc)
        resp = self.client.post(_reviews_url(self.listing.id), {"rating": 4})
        assert resp.status_code == 403

    def test_admin_gets_403(self):
        admin = _user("cr_admin_role@test.com", UserRole.ADMIN)
        self.client.force_authenticate(user=admin)
        resp = self.client.post(_reviews_url(self.listing.id), {"rating": 4})
        assert resp.status_code == 403

    def test_anonymous_gets_401(self):
        resp = self.client.post(_reviews_url(self.listing.id), {"rating": 4})
        assert resp.status_code == 401

    def test_rating_below_1_gets_400(self):
        family = _user("cr_rmin@test.com")
        self.client.force_authenticate(user=family)
        resp = self.client.post(_reviews_url(self.listing.id), {"rating": 0})
        assert resp.status_code == 400

    def test_rating_above_5_gets_400(self):
        family = _user("cr_rmax@test.com")
        self.client.force_authenticate(user=family)
        resp = self.client.post(_reviews_url(self.listing.id), {"rating": 6})
        assert resp.status_code == 400

    def test_second_review_same_listing_gets_409(self):
        family = _user("cr_dup@test.com")
        listing = _listing(ListingCategory.SCHOOLS)
        Review.objects.create(listing=listing, author=family, rating=3)
        self.client.force_authenticate(user=family)
        resp = self.client.post(_reviews_url(listing.id), {"rating": 5})
        assert resp.status_code == 409
