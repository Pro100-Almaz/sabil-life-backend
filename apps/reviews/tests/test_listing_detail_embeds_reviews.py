"""
Tests for the embedded reviews[] in GET /api/v1/listings/{id}/ — Phase 7.

The Phase 2 stub returned []. Phase 7 replaces it with real review data
capped at 10 entries.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.reviews.models import Review
from apps.users.enums import UserRole

User = get_user_model()


def _user(email, role=UserRole.FAMILY, full_name=""):
    return User.objects.create_user(
        email=email, password="pass1234!", role=role, full_name=full_name
    )


def _listing(title="Embed Test"):
    return Listing.objects.create(
        title=title, category=ListingCategory.SCHOOLS, status=ListingStatus.ACTIVE
    )


def _detail_url(listing_id):
    return reverse("v1:catalog:listings-detail", kwargs={"id": str(listing_id)})


@pytest.mark.django_db
class TestListingDetailEmbedsReviews:
    def setup_method(self):
        self.client = APIClient()

    def test_listing_detail_has_reviews_key(self):
        listing = _listing("Has Reviews Key")
        resp = self.client.get(_detail_url(listing.id))
        assert resp.status_code == 200
        assert "reviews" in resp.json()

    def test_listing_detail_reviews_empty_when_no_reviews(self):
        listing = _listing("No Reviews")
        resp = self.client.get(_detail_url(listing.id))
        assert resp.json()["reviews"] == []

    def test_listing_detail_reviews_populated(self):
        listing = _listing("Has Reviews")
        family = _user("emb_one@test.com", full_name="Aisha")
        Review.objects.create(listing=listing, author=family, rating=5, text="Excellent!")
        resp = self.client.get(_detail_url(listing.id))
        data = resp.json()
        assert len(data["reviews"]) == 1
        assert data["reviews"][0]["rating"] == 5
        assert data["reviews"][0]["text"] == "Excellent!"
        assert data["reviews"][0]["author_name"] == "Aisha"

    def test_listing_detail_reviews_capped_at_10(self):
        listing = _listing("Many Reviews")
        for i in range(12):
            family = _user(f"emb_cap{i}@test.com")
            Review.objects.create(listing=listing, author=family, rating=4)
        resp = self.client.get(_detail_url(listing.id))
        data = resp.json()
        assert len(data["reviews"]) == 10

    def test_full_list_available_at_reviews_endpoint(self):
        """The full list (>10) is at /listings/{id}/reviews/."""
        listing = _listing("Full List")
        for i in range(12):
            family = _user(f"emb_full{i}@test.com")
            Review.objects.create(listing=listing, author=family, rating=3)

        reviews_url = reverse(
            "v1:listing-reviews", kwargs={"listing_id": str(listing.id)}
        )
        resp = self.client.get(reviews_url)
        data = resp.json()
        assert data["count"] == 12

    def test_listing_rating_updates_in_detail_after_review(self):
        """Listing.rating in detail response reflects the recomputed value."""
        listing = _listing("Rating Check")
        family = _user("emb_rating@test.com")
        Review.objects.create(listing=listing, author=family, rating=5)
        resp = self.client.get(_detail_url(listing.id))
        assert float(resp.json()["rating"]) == 5.0
        assert resp.json()["review_count"] == 1

    def test_reviews_author_email_not_exposed_in_embed(self):
        listing = _listing("No Email Embed")
        family = _user("emb_noemail@test.com", full_name="Private")
        Review.objects.create(listing=listing, author=family, rating=4)
        resp = self.client.get(_detail_url(listing.id))
        review_entry = resp.json()["reviews"][0]
        assert "email" not in review_entry
