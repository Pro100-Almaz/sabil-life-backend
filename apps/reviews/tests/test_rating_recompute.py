"""
Tests for the rating recompute service and signal — Phase 7.

Covers: 0 reviews, 1 review, multiple reviews, delete, rounding.
"""

import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.reviews.models import Review
from apps.reviews.services import recompute_listing_rating
from apps.users.enums import UserRole

User = get_user_model()


def _user(email, role=UserRole.FAMILY):
    return User.objects.create_user(email=email, password="pass1234!", role=role)


def _listing(title="Recompute Listing"):
    return Listing.objects.create(
        title=title, category=ListingCategory.TUTORING, status=ListingStatus.ACTIVE
    )


@pytest.mark.django_db
class TestRecomputeListingRating:
    def test_zero_reviews_gives_zero_rating(self):
        listing = _listing("Zero Reviews")
        recompute_listing_rating(listing)
        listing.refresh_from_db()
        assert float(listing.rating) == 0.0
        assert listing.review_count == 0

    def test_one_review_of_five(self):
        listing = _listing("One Review")
        family = _user("rc_one@test.com")
        Review.objects.create(listing=listing, author=family, rating=5)
        listing.refresh_from_db()
        assert float(listing.rating) == 5.0
        assert listing.review_count == 1

    def test_two_reviews_average(self):
        listing = _listing("Two Reviews")
        f1 = _user("rc_two1@test.com")
        f2 = _user("rc_two2@test.com")
        Review.objects.create(listing=listing, author=f1, rating=3)
        Review.objects.create(listing=listing, author=f2, rating=5)
        listing.refresh_from_db()
        assert float(listing.rating) == 4.0
        assert listing.review_count == 2

    def test_delete_review_recomputes(self):
        listing = _listing("Delete Review")
        f1 = _user("rc_del1@test.com")
        f2 = _user("rc_del2@test.com")
        r1 = Review.objects.create(listing=listing, author=f1, rating=2)
        Review.objects.create(listing=listing, author=f2, rating=4)
        listing.refresh_from_db()
        assert listing.review_count == 2

        r1.delete()
        listing.refresh_from_db()
        assert listing.review_count == 1
        assert float(listing.rating) == 4.0

    def test_delete_all_reviews_resets_to_zero(self):
        listing = _listing("Delete All")
        family = _user("rc_dall@test.com")
        r = Review.objects.create(listing=listing, author=family, rating=5)
        r.delete()
        listing.refresh_from_db()
        assert float(listing.rating) == 0.0
        assert listing.review_count == 0

    def test_rating_rounds_to_one_decimal_place(self):
        """Three reviews of 3, 4, 5 → average 4.0 (exact); test rounding with 4.333."""
        listing = _listing("Rounding Listing")
        f1 = _user("rc_rnd1@test.com")
        f2 = _user("rc_rnd2@test.com")
        f3 = _user("rc_rnd3@test.com")
        # ratings: 4, 4, 5 → avg = 4.333...
        Review.objects.create(listing=listing, author=f1, rating=4)
        Review.objects.create(listing=listing, author=f2, rating=4)
        Review.objects.create(listing=listing, author=f3, rating=5)
        listing.refresh_from_db()
        # round(4.333, 1) = 4.3
        assert float(listing.rating) == 4.3
        assert listing.review_count == 3

    def test_signal_fires_on_create(self):
        """post_save signal fires automatically — no manual recompute needed."""
        listing = _listing("Signal Create")
        family = _user("rc_sig_c@test.com")
        assert listing.review_count == 0
        Review.objects.create(listing=listing, author=family, rating=5)
        listing.refresh_from_db()
        assert listing.review_count == 1

    def test_signal_fires_on_update(self):
        """post_save fires on update — rating recomputes after PATCH."""
        listing = _listing("Signal Update")
        family = _user("rc_sig_u@test.com")
        review = Review.objects.create(listing=listing, author=family, rating=5)
        listing.refresh_from_db()
        assert float(listing.rating) == 5.0

        review.rating = 2
        review.save()
        listing.refresh_from_db()
        assert float(listing.rating) == 2.0

    def test_signal_fires_on_delete(self):
        """post_delete signal fires — review_count drops after delete."""
        listing = _listing("Signal Delete")
        family = _user("rc_sig_d@test.com")
        review = Review.objects.create(listing=listing, author=family, rating=4)
        listing.refresh_from_db()
        assert listing.review_count == 1

        review.delete()
        listing.refresh_from_db()
        assert listing.review_count == 0
