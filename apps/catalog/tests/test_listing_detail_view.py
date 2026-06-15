"""
Tests for GET /api/v1/listings/{id}/ (detail endpoint).

Covers: full field shape, owner_id, reviews=[], 404 for non-ACTIVE, 404 for unknown UUID.
"""

import uuid

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Listing, ListingCategory, ListingStatus

User = get_user_model()


def make_listing(**kwargs) -> Listing:
    defaults = {
        "title": "Detail Listing",
        "category": ListingCategory.TUTORING,
        "status": ListingStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Listing.objects.create(**defaults)


class ListingDetailViewTests(APITestCase):
    """Tests for GET /api/v1/listings/{id}/."""

    def _url(self, listing_id) -> str:
        return reverse("v1:catalog:listings-detail", kwargs={"id": str(listing_id)})

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_detail_returns_200_for_active_listing(self):
        listing = make_listing()
        response = self.client.get(self._url(listing.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_detail_contains_all_required_fields(self):
        listing = make_listing(
            title="Full Detail",
            description="A full description.",
            highlights=["Point A", "Point B"],
        )
        response = self.client.get(self._url(listing.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        card_fields = [
            "id",
            "title",
            "category",
            "subtitle",
            "neighborhood",
            "lat",
            "lng",
            "rating",
            "review_count",
            "price_from_qar",
            "image_urls",
            "age_groups",
            "is_featured",
            "distance_km",
        ]
        detail_extra_fields = ["description", "highlights", "owner_id", "reviews"]

        for field in card_fields + detail_extra_fields:
            self.assertIn(field, data, f"Field '{field}' missing from detail response")

    def test_detail_reviews_is_empty_list(self):
        """Phase 2: reviews is always [] until Phase 7."""
        listing = make_listing()
        response = self.client.get(self._url(listing.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["reviews"], [])

    def test_detail_owner_id_is_null_for_admin_entered_listing(self):
        """Listings without an owner return owner_id=null."""
        listing = make_listing(owner=None)
        response = self.client.get(self._url(listing.id))
        self.assertIsNone(response.data["owner_id"])

    def test_detail_owner_id_is_string_for_provider_owned(self):
        """owner_id is a non-null string (the owner's PK) when the listing has an owner.

        CustomUser uses BigAutoField (integer) primary keys, so owner_id is an
        integer stringified — NOT a UUID.  We just verify it is non-null and that
        it matches str(owner.pk).
        """
        owner = User.objects.create_user(
            email="provider@example.com", password="StrongPass!99"
        )
        listing = make_listing(owner=owner)
        response = self.client.get(self._url(listing.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        owner_id = response.data["owner_id"]
        self.assertIsNotNone(owner_id)
        # owner_id must match str(owner.pk)
        self.assertEqual(owner_id, str(owner.pk))

    def test_detail_description_and_highlights_present(self):
        listing = make_listing(
            description="Detailed description here.",
            highlights=["Flexible hours", "Native speakers"],
        )
        response = self.client.get(self._url(listing.id))
        self.assertEqual(response.data["description"], "Detailed description here.")
        self.assertEqual(
            response.data["highlights"], ["Flexible hours", "Native speakers"]
        )

    # ------------------------------------------------------------------
    # 404 cases
    # ------------------------------------------------------------------

    def test_detail_returns_404_for_draft_listing(self):
        listing = make_listing(status=ListingStatus.DRAFT)
        response = self.client.get(self._url(listing.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_returns_404_for_pending_listing(self):
        listing = make_listing(status=ListingStatus.PENDING)
        response = self.client.get(self._url(listing.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_returns_404_for_rejected_listing(self):
        listing = make_listing(status=ListingStatus.REJECTED)
        response = self.client.get(self._url(listing.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_returns_404_for_unknown_uuid(self):
        unknown_id = uuid.uuid4()
        response = self.client.get(self._url(unknown_id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------
    # Public access
    # ------------------------------------------------------------------

    def test_detail_does_not_require_authentication(self):
        listing = make_listing()
        # No credentials set — should still return 200
        response = self.client.get(self._url(listing.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # Phase 5: private fields must NOT appear in public detail response
    # ------------------------------------------------------------------

    def test_session_schedule_not_in_detail_response(self):
        """Phase 5 private field must never leak on public listing detail."""
        listing = make_listing()
        response = self.client.get(self._url(listing.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn("session_schedule", response.data)

    def test_exact_address_not_in_detail_response(self):
        listing = make_listing()
        response = self.client.get(self._url(listing.id))
        self.assertNotIn("exact_address", response.data)

    def test_materials_required_not_in_detail_response(self):
        listing = make_listing()
        response = self.client.get(self._url(listing.id))
        self.assertNotIn("materials_required", response.data)
