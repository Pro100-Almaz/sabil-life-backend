"""
Tests for GET /api/v1/listings/{listing_id}/reviews/ — Phase 7.

Covers public access, ordering, pagination, author_name fallback,
and absence of sensitive fields.
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


def _listing(title="List View Listing"):
    return Listing.objects.create(
        title=title, category=ListingCategory.SCHOOLS, status=ListingStatus.ACTIVE
    )


def _reviews_url(listing_id):
    return reverse("v1:listing-reviews", kwargs={"listing_id": str(listing_id)})


@pytest.mark.django_db
class TestReviewListView:
    def setup_method(self):
        self.client = APIClient()

    def test_public_access_returns_200(self):
        listing = _listing("Public Access")
        resp = self.client.get(_reviews_url(listing.id))
        assert resp.status_code == 200

    def test_empty_listing_returns_empty_results(self):
        listing = _listing("Empty")
        resp = self.client.get(_reviews_url(listing.id))
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []

    def test_reviews_ordered_most_recent_first(self):
        listing = _listing("Ordered")
        f1 = _user("lv_ord1@test.com", full_name="Alice")
        f2 = _user("lv_ord2@test.com", full_name="Bob")
        r1 = Review.objects.create(listing=listing, author=f1, rating=3)
        r2 = Review.objects.create(listing=listing, author=f2, rating=5)
        resp = self.client.get(_reviews_url(listing.id))
        results = resp.json()["results"]
        assert len(results) == 2
        assert results[0]["id"] == str(r2.id)
        assert results[1]["id"] == str(r1.id)

    def test_author_name_shows_full_name(self):
        listing = _listing("Author Name")
        family = _user("lv_an@test.com", full_name="Sara Al-Kuwari")
        Review.objects.create(listing=listing, author=family, rating=4)
        resp = self.client.get(_reviews_url(listing.id))
        result = resp.json()["results"][0]
        assert result["author_name"] == "Sara Al-Kuwari"

    def test_author_name_falls_back_to_anonymous(self):
        listing = _listing("Anon Author")
        family = _user("lv_anon@test.com", full_name="")
        Review.objects.create(listing=listing, author=family, rating=3)
        resp = self.client.get(_reviews_url(listing.id))
        result = resp.json()["results"][0]
        assert result["author_name"] == "Anonymous"

    def test_author_email_not_in_response(self):
        listing = _listing("No Email")
        family = _user("lv_noemail@test.com", full_name="Private User")
        Review.objects.create(listing=listing, author=family, rating=5)
        resp = self.client.get(_reviews_url(listing.id))
        result = resp.json()["results"][0]
        assert "email" not in result

    def test_author_id_in_response(self):
        listing = _listing("Has Author ID")
        family = _user("lv_noid@test.com", full_name="Hidden User")
        Review.objects.create(listing=listing, author=family, rating=5)
        resp = self.client.get(_reviews_url(listing.id))
        result = resp.json()["results"][0]
        assert result["author_id"] == family.id

    def test_response_fields(self):
        listing = _listing("Fields Check")
        family = _user("lv_fields@test.com", full_name="Field Tester")
        Review.objects.create(listing=listing, author=family, rating=4, text="Good")
        resp = self.client.get(_reviews_url(listing.id))
        result = resp.json()["results"][0]
        assert set(result.keys()) == {"id", "rating", "text", "author_name", "author_id", "created_at"}

    def test_paginated_response_shape(self):
        listing = _listing("Paginated")
        resp = self.client.get(_reviews_url(listing.id))
        data = resp.json()
        assert "count" in data
        assert "results" in data

    def test_listing_not_found_returns_404(self):
        import uuid

        resp = self.client.get(_reviews_url(uuid.uuid4()))
        assert resp.status_code == 404

    def test_inactive_listing_returns_404(self):
        listing = Listing.objects.create(
            title="Draft", category=ListingCategory.SCHOOLS, status=ListingStatus.DRAFT
        )
        resp = self.client.get(_reviews_url(listing.id))
        assert resp.status_code == 404
