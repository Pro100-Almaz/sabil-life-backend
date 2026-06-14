"""
Tests for distance annotation and sorting.

Covers:
- ?sort=distance&lat=...&lng=... orders results by haversine distance.
- ?max_distance_km= excludes listings outside the radius.
- Listings with null lat/lng sort last (get NULL distance_km).
- Spot-check: listing at the query point reports ~0 km distance.
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.catalog.services import haversine_km

# Reference point: West Bay, Doha (used in spec smoke test)
REF_LAT = 25.369
REF_LNG = 51.551


def make_listing(**kwargs) -> Listing:
    defaults = {
        "title": "Distance Listing",
        "category": ListingCategory.ACTIVITIES,
        "status": ListingStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Listing.objects.create(**defaults)


class DistanceSortTests(APITestCase):
    """Tests for geo-distance annotation and sorting."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("v1:catalog:listings-list")

    # ------------------------------------------------------------------
    # Ordering
    # ------------------------------------------------------------------

    def test_sort_distance_orders_nearest_first(self):
        """Listings closer to the reference point appear earlier in results."""
        near = make_listing(title="Near", lat=25.370, lng=51.552)  # ~0.1 km away
        far = make_listing(title="Far", lat=25.500, lng=51.700)  # ~19 km away

        response = self.client.get(
            self.url,
            {"sort": "distance", "lat": str(REF_LAT), "lng": str(REF_LNG)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in response.data["results"]]
        self.assertIn(str(near.id), ids)
        self.assertIn(str(far.id), ids)
        self.assertLess(ids.index(str(near.id)), ids.index(str(far.id)))

    def test_distance_km_present_in_results_when_lat_lng_provided(self):
        """distance_km field is non-None when lat/lng query params are given."""
        make_listing(title="Has Coords", lat=25.369, lng=51.551)

        response = self.client.get(
            self.url,
            {"lat": str(REF_LAT), "lng": str(REF_LNG)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data["results"][0]
        self.assertIsNotNone(result["distance_km"])

    # ------------------------------------------------------------------
    # Spot-check: zero distance
    # ------------------------------------------------------------------

    def test_listing_at_exact_ref_point_has_near_zero_distance(self):
        """A listing at exactly (REF_LAT, REF_LNG) should report ~0 km."""
        make_listing(title="At Origin", lat=REF_LAT, lng=REF_LNG)

        response = self.client.get(
            self.url,
            {"lat": str(REF_LAT), "lng": str(REF_LNG)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data["results"][0]
        distance = result["distance_km"]
        self.assertIsNotNone(distance)
        self.assertAlmostEqual(float(distance), 0.0, delta=0.1)

    # ------------------------------------------------------------------
    # Haversine math spot-check (pure Python vs ORM)
    # ------------------------------------------------------------------

    def test_distance_km_matches_python_haversine_within_tolerance(self):
        """
        The ORM-annotated distance should match the pure-Python haversine
        to within 0.5 km (formula rounding from float arithmetic).
        """
        listing_lat, listing_lng = 25.285, 51.531  # ~10 km south of ref point
        make_listing(title="Math Check", lat=listing_lat, lng=listing_lng)

        response = self.client.get(
            self.url,
            {"lat": str(REF_LAT), "lng": str(REF_LNG)},
        )
        result = response.data["results"][0]
        orm_distance = float(result["distance_km"])
        py_distance = haversine_km(REF_LAT, REF_LNG, listing_lat, listing_lng)

        self.assertAlmostEqual(orm_distance, py_distance, delta=0.5)

    # ------------------------------------------------------------------
    # max_distance_km radius filter
    # ------------------------------------------------------------------

    def test_max_distance_km_excludes_distant_listings(self):
        """Listings beyond max_distance_km are excluded from results."""
        nearby = make_listing(title="Nearby", lat=25.370, lng=51.552)  # ~0.1 km
        distant = make_listing(title="Distant", lat=25.600, lng=51.800)  # ~30+ km

        response = self.client.get(
            self.url,
            {
                "max_distance_km": "5",
                "lat": str(REF_LAT),
                "lng": str(REF_LNG),
                "sort": "distance",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in response.data["results"]]
        self.assertIn(str(nearby.id), ids)
        self.assertNotIn(str(distant.id), ids)

    def test_max_distance_km_without_lat_lng_returns_unfiltered(self):
        """
        If max_distance_km is given but lat/lng are absent, we cannot annotate
        distance, so the filter is silently ignored and all ACTIVE listings appear.
        """
        make_listing(title="Listing A", lat=25.370, lng=51.552)
        make_listing(title="Listing B", lat=25.600, lng=51.800)

        response = self.client.get(self.url, {"max_distance_km": "5"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Both listings should be present (no lat/lng → no distance filter)
        self.assertEqual(response.data["count"], 2)

    # ------------------------------------------------------------------
    # Null-coordinate listings sort last
    # ------------------------------------------------------------------

    def test_null_coord_listings_have_null_distance_km(self):
        """Listings with null lat/lng get distance_km=None in the response."""
        make_listing(title="No Coords", lat=None, lng=None)

        response = self.client.get(
            self.url,
            {"lat": str(REF_LAT), "lng": str(REF_LNG)},
        )
        result = response.data["results"][0]
        # distance_km should be None for a null-coord listing
        self.assertIsNone(result["distance_km"])

    def test_null_coord_listings_sort_after_coord_listings(self):
        """When sorting by distance, null-coord listings appear last."""
        no_coords = make_listing(title="No Coords", lat=None, lng=None)
        with_coords = make_listing(title="Has Coords", lat=25.370, lng=51.552)

        response = self.client.get(
            self.url,
            {"sort": "distance", "lat": str(REF_LAT), "lng": str(REF_LNG)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in response.data["results"]]
        # The listing with coordinates should appear before the null-coord one
        self.assertLess(
            ids.index(str(with_coords.id)),
            ids.index(str(no_coords.id)),
        )

    # ------------------------------------------------------------------
    # sort=distance without lat/lng silently falls back
    # ------------------------------------------------------------------

    def test_sort_distance_without_lat_lng_returns_200(self):
        """?sort=distance without lat/lng must not crash — returns 200."""
        make_listing(title="No Geo Sort")
        response = self.client.get(self.url, {"sort": "distance"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # Pure-Python haversine utility
    # ------------------------------------------------------------------

    def test_haversine_km_zero_distance(self):
        """haversine_km(p, p) == 0."""
        self.assertAlmostEqual(
            haversine_km(REF_LAT, REF_LNG, REF_LAT, REF_LNG), 0.0, delta=1e-6
        )

    def test_haversine_km_known_distance(self):
        """
        Doha (25.286, 51.536) to West Bay (25.369, 51.551) is approximately 9.3 km.
        Allow ±1 km tolerance.
        """
        d = haversine_km(25.286, 51.536, 25.369, 51.551)
        self.assertAlmostEqual(d, 9.3, delta=1.0)
