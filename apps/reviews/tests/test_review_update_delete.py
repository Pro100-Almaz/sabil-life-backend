"""
Tests for PATCH/DELETE /api/v1/reviews/{id}/ — Phase 7.

Covers: own review update/delete, recompute fires, 404 on other's review.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.reviews.models import Review
from apps.users.enums import UserRole

User = get_user_model()


def _user(email, role=UserRole.FAMILY, **kw):
    return User.objects.create_user(email=email, password="pass1234!", role=role, **kw)


def _listing(title="Update Listing"):
    return Listing.objects.create(
        title=title, category=ListingCategory.SCHOOLS, status=ListingStatus.ACTIVE
    )


def _review_url(review_id):
    return reverse("v1:review-detail", kwargs={"review_id": str(review_id)})


@pytest.mark.django_db
class TestReviewUpdate:
    def setup_method(self):
        self.client = APIClient()
        self.family = _user("upd_fam@test.com", full_name="Updater")
        self.listing = _listing("Update Test")
        self.review = Review.objects.create(
            listing=self.listing, author=self.family, rating=3, text="Okay"
        )

    def test_patch_own_review_returns_200(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.patch(_review_url(self.review.id), {"rating": 5})
        assert resp.status_code == 200

    def test_patch_updates_rating(self):
        self.client.force_authenticate(user=self.family)
        self.client.patch(_review_url(self.review.id), {"rating": 5})
        self.review.refresh_from_db()
        assert self.review.rating == 5

    def test_patch_updates_text(self):
        self.client.force_authenticate(user=self.family)
        self.client.patch(_review_url(self.review.id), {"text": "Updated text"})
        self.review.refresh_from_db()
        assert self.review.text == "Updated text"

    def test_patch_triggers_recompute(self):
        self.client.force_authenticate(user=self.family)
        self.client.patch(_review_url(self.review.id), {"rating": 5})
        self.listing.refresh_from_db()
        assert float(self.listing.rating) == 5.0

    def test_patch_other_family_review_returns_404(self):
        other = _user("upd_other@test.com")
        other_review = Review.objects.create(listing=self.listing, author=other, rating=2)
        self.client.force_authenticate(user=self.family)
        resp = self.client.patch(_review_url(other_review.id), {"rating": 5})
        assert resp.status_code == 404

    def test_patch_invalid_rating_returns_400(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.patch(_review_url(self.review.id), {"rating": 10})
        assert resp.status_code == 400

    def test_patch_unauthenticated_returns_401(self):
        resp = self.client.patch(_review_url(self.review.id), {"rating": 5})
        assert resp.status_code == 401


@pytest.mark.django_db
class TestReviewDelete:
    def setup_method(self):
        self.client = APIClient()
        self.family = _user("del_fam@test.com", full_name="Deleter")
        self.listing = _listing("Delete Test")
        self.review = Review.objects.create(
            listing=self.listing, author=self.family, rating=4
        )

    def test_delete_own_review_returns_204(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.delete(_review_url(self.review.id))
        assert resp.status_code == 204

    def test_delete_removes_review_from_db(self):
        self.client.force_authenticate(user=self.family)
        self.client.delete(_review_url(self.review.id))
        assert not Review.objects.filter(pk=self.review.id).exists()

    def test_delete_triggers_recompute_to_zero(self):
        self.client.force_authenticate(user=self.family)
        self.client.delete(_review_url(self.review.id))
        self.listing.refresh_from_db()
        assert float(self.listing.rating) == 0.0
        assert self.listing.review_count == 0

    def test_delete_other_family_review_returns_404(self):
        other = _user("del_other@test.com")
        other_review = Review.objects.create(listing=self.listing, author=other, rating=3)
        self.client.force_authenticate(user=self.family)
        resp = self.client.delete(_review_url(other_review.id))
        assert resp.status_code == 404

    def test_delete_unauthenticated_returns_401(self):
        resp = self.client.delete(_review_url(self.review.id))
        assert resp.status_code == 401

    def test_delete_recompute_with_remaining_review(self):
        """After deleting one of two reviews, rating reflects the survivor."""
        other_family = _user("del_remain@test.com")
        Review.objects.create(listing=self.listing, author=other_family, rating=2)

        self.listing.refresh_from_db()
        assert self.listing.review_count == 2

        self.client.force_authenticate(user=self.family)
        self.client.delete(_review_url(self.review.id))

        self.listing.refresh_from_db()
        assert self.listing.review_count == 1
        assert float(self.listing.rating) == 2.0
