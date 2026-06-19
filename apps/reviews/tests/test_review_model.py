"""
Tests for the Review model — Phase 7.

Covers: field defaults, unique constraint, rating validators (1-5), ordering.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.reviews.models import Review
from apps.users.enums import UserRole

User = get_user_model()


def _user(email, role=UserRole.FAMILY):
    return User.objects.create_user(email=email, password="pass1234!", role=role)


def _listing(title="Test Listing", category=ListingCategory.TUTORING):
    return Listing.objects.create(
        title=title, category=category, status=ListingStatus.ACTIVE
    )


@pytest.mark.django_db
class TestReviewModel:
    def test_review_creates_with_defaults(self):
        family = _user("m_defaults@test.com")
        listing = _listing("Defaults Listing")
        review = Review.objects.create(listing=listing, author=family, rating=4)
        assert review.text == ""
        assert review.id is not None
        assert review.created_at is not None
        assert review.updated_at is not None

    def test_review_str(self):
        family = _user("m_str@test.com")
        listing = _listing("Str Listing")
        review = Review.objects.create(listing=listing, author=family, rating=3)
        s = str(review)
        assert "3" in s

    def test_review_ordering_most_recent_first(self):
        family = _user("m_order@test.com")
        listing = _listing("Order Listing")
        r1 = Review.objects.create(listing=listing, author=family, rating=3)
        family2 = _user("m_order2@test.com")
        r2 = Review.objects.create(listing=listing, author=family2, rating=5)
        reviews = list(Review.objects.filter(listing=listing))
        # Most recent first — r2 was created after r1
        assert reviews[0].id == r2.id
        assert reviews[1].id == r1.id

    def test_unique_constraint_listing_author(self):
        family = _user("m_unique@test.com")
        listing = _listing("Unique Listing")
        Review.objects.create(listing=listing, author=family, rating=4)
        with pytest.raises(IntegrityError):
            Review.objects.create(listing=listing, author=family, rating=5)

    def test_different_authors_can_review_same_listing(self):
        listing = _listing("Multi-author Listing")
        f1 = _user("m_ma1@test.com")
        f2 = _user("m_ma2@test.com")
        Review.objects.create(listing=listing, author=f1, rating=4)
        Review.objects.create(listing=listing, author=f2, rating=5)
        assert Review.objects.filter(listing=listing).count() == 2

    def test_same_author_can_review_different_listings(self):
        family = _user("m_diff@test.com")
        l1 = _listing("Listing A")
        l2 = _listing("Listing B")
        Review.objects.create(listing=l1, author=family, rating=4)
        Review.objects.create(listing=l2, author=family, rating=5)
        assert Review.objects.filter(author=family).count() == 2

    def test_rating_validator_minimum(self):
        family = _user("m_rmin@test.com")
        listing = _listing("Min Rating Listing")
        review = Review(listing=listing, author=family, rating=0)
        with pytest.raises(ValidationError):
            review.full_clean()

    def test_rating_validator_maximum(self):
        family = _user("m_rmax@test.com")
        listing = _listing("Max Rating Listing")
        review = Review(listing=listing, author=family, rating=6)
        with pytest.raises(ValidationError):
            review.full_clean()

    def test_rating_1_is_valid(self):
        family = _user("m_r1@test.com")
        listing = _listing("R1 Listing")
        review = Review(listing=listing, author=family, rating=1)
        review.full_clean()  # should not raise

    def test_rating_5_is_valid(self):
        family = _user("m_r5@test.com")
        listing = _listing("R5 Listing")
        review = Review(listing=listing, author=family, rating=5)
        review.full_clean()  # should not raise
