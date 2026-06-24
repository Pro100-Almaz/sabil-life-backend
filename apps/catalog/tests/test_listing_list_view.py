"""
Tests for GET /api/v1/listings/ (list endpoint).

Covers: public access, status filtering, pagination shape, category/q/price/age
filters, and sort by rating / price_low.
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Listing, ListingCategory, ListingStatus


def make_listing(**kwargs) -> Listing:
    defaults = {
        "title": "Default Listing",
        "category": ListingCategory.TUTORING,
        "status": ListingStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Listing.objects.create(**defaults)


class ListingListViewTests(APITestCase):
    """Tests for GET /api/v1/listings/."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("v1:catalog:listings-list")

    # ------------------------------------------------------------------
    # Public access
    # ------------------------------------------------------------------

    def test_public_access_returns_200(self):
        """No authentication required."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # Status filtering — only ACTIVE listings returned
    # ------------------------------------------------------------------

    def test_only_active_listings_returned(self):
        """DRAFT, PENDING, REJECTED listings are excluded."""
        active = make_listing(title="Active One", status=ListingStatus.ACTIVE)
        make_listing(title="Draft One", status=ListingStatus.DRAFT)
        make_listing(title="Pending One", status=ListingStatus.PENDING)
        make_listing(title="Rejected One", status=ListingStatus.REJECTED)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in response.data["results"]]
        self.assertIn(str(active.id), ids)
        self.assertEqual(len(ids), 1)

    # ------------------------------------------------------------------
    # Pagination shape
    # ------------------------------------------------------------------

    def test_pagination_shape(self):
        """Response must have count, next, previous, results keys."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in ("count", "next", "previous", "results"):
            self.assertIn(key, response.data)

    def test_results_is_a_list(self):
        response = self.client.get(self.url)
        self.assertIsInstance(response.data["results"], list)

    # ------------------------------------------------------------------
    # Category filter
    # ------------------------------------------------------------------

    def test_category_filter_uppercase(self):
        """?category=TUTORING returns only TUTORING listings."""
        tutoring = make_listing(title="Math Tutor", category=ListingCategory.TUTORING)
        make_listing(title="Nursery ABC", category=ListingCategory.NURSERIES)

        response = self.client.get(self.url, {"category": "TUTORING"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in response.data["results"]]
        self.assertIn(str(tutoring.id), ids)
        self.assertEqual(len(ids), 1)

    def test_category_filter_lowercase(self):
        """?category=tutoring (lowercase) must work identically."""
        tutoring = make_listing(title="Science Tutor", category=ListingCategory.TUTORING)
        make_listing(title="School XYZ", category=ListingCategory.SCHOOLS)

        response = self.client.get(self.url, {"category": "tutoring"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in response.data["results"]]
        self.assertIn(str(tutoring.id), ids)
        self.assertEqual(len(ids), 1)

    # ------------------------------------------------------------------
    # Search filter (q)
    # ------------------------------------------------------------------

    def test_search_filter_matches_title(self):
        listing = make_listing(title="Bright Stars Academy")
        make_listing(title="Another Place")

        response = self.client.get(self.url, {"search": "bright"})
        ids = [r["id"] for r in response.data["results"]]
        self.assertIn(str(listing.id), ids)
        self.assertEqual(len(ids), 1)

    def test_search_filter_matches_subtitle(self):
        listing = make_listing(title="Generic Title", subtitle="Expert coding lessons")
        make_listing(title="Other Listing", subtitle="Something else")

        response = self.client.get(self.url, {"search": "coding"})
        ids = [r["id"] for r in response.data["results"]]
        self.assertIn(str(listing.id), ids)
        self.assertEqual(len(ids), 1)

    def test_search_filter_case_insensitive(self):
        listing = make_listing(title="Creative Arts Studio")
        response = self.client.get(self.url, {"search": "CREATIVE"})
        ids = [r["id"] for r in response.data["results"]]
        self.assertIn(str(listing.id), ids)

    # ------------------------------------------------------------------
    # Price filter
    # ------------------------------------------------------------------

    def test_price_max_excludes_expensive_listings(self):
        cheap = make_listing(title="Cheap", price_from_qar=50)
        make_listing(title="Expensive", price_from_qar=200)

        response = self.client.get(self.url, {"price_max": "100"})
        ids = [r["id"] for r in response.data["results"]]
        self.assertIn(str(cheap.id), ids)
        self.assertEqual(len(ids), 1)

    def test_price_max_inclusive(self):
        """?price_max=100 includes a listing priced exactly 100."""
        exact = make_listing(title="Exact 100", price_from_qar=100)
        response = self.client.get(self.url, {"price_max": "100"})
        ids = [r["id"] for r in response.data["results"]]
        self.assertIn(str(exact.id), ids)

    # ------------------------------------------------------------------
    # Age filter
    # ------------------------------------------------------------------

    def test_age_filter_matches_json_list_member(self):
        listing = make_listing(title="Kids Club", age_groups=["3-6", "5-8"])
        make_listing(title="Teen Club", age_groups=["12-16"])

        response = self.client.get(self.url, {"age": "5-8"})
        ids = [r["id"] for r in response.data["results"]]
        self.assertIn(str(listing.id), ids)
        self.assertEqual(len(ids), 1)

    def test_age_filter_no_partial_match(self):
        """?age=5 must NOT match age_groups=["5-8"]."""
        make_listing(title="Kids", age_groups=["5-8"])
        response = self.client.get(self.url, {"age": "5"})
        self.assertEqual(len(response.data["results"]), 0)

    # ------------------------------------------------------------------
    # Sort
    # ------------------------------------------------------------------

    def test_sort_rating_orders_highest_first(self):
        from decimal import Decimal

        low = make_listing(title="Low rated", rating=Decimal("2.5"))
        high = make_listing(title="High rated", rating=Decimal("4.9"))

        response = self.client.get(self.url, {"sort": "rating"})
        ids = [r["id"] for r in response.data["results"]]
        self.assertLess(ids.index(str(high.id)), ids.index(str(low.id)))

    def test_sort_price_low_orders_cheapest_first(self):
        expensive = make_listing(title="Expensive", price_from_qar=500)
        cheap = make_listing(title="Cheap", price_from_qar=10)

        response = self.client.get(self.url, {"sort": "price_low"})
        ids = [r["id"] for r in response.data["results"]]
        self.assertLess(ids.index(str(cheap.id)), ids.index(str(expensive.id)))

    # ------------------------------------------------------------------
    # Response field shape
    # ------------------------------------------------------------------

    def test_list_result_contains_expected_fields(self):
        make_listing(title="Shape Test")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if response.data["results"]:
            result = response.data["results"][0]
            for field in (
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
            ):
                self.assertIn(field, result)

    def test_distance_km_is_none_when_no_lat_lng(self):
        make_listing(title="No coords", lat=None, lng=None)
        response = self.client.get(self.url)
        result = response.data["results"][0]
        self.assertIsNone(result["distance_km"])

    # ------------------------------------------------------------------
    # Phase 5: private fields must NOT appear in public list response
    # ------------------------------------------------------------------

    def test_session_schedule_not_in_list_response(self):
        """Phase 5 private field must never leak on public listing list."""
        make_listing(title="Private Fields Test")
        response = self.client.get(self.url)
        for result in response.data["results"]:
            self.assertNotIn("session_schedule", result)

    def test_exact_address_not_in_list_response(self):
        make_listing(title="Private Fields Test 2")
        response = self.client.get(self.url)
        for result in response.data["results"]:
            self.assertNotIn("exact_address", result)

    def test_materials_required_not_in_list_response(self):
        make_listing(title="Private Fields Test 3")
        response = self.client.get(self.url)
        for result in response.data["results"]:
            self.assertNotIn("materials_required", result)
