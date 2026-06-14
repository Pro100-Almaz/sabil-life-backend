"""
Tests for GET /api/v1/categories/.

Covers: all 7 categories returned, correct ACTIVE counts, zero-count categories
included, public access.
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Listing, ListingCategory, ListingStatus

ALL_CATEGORIES = [choice[0] for choice in ListingCategory.choices]


def make_listing(**kwargs) -> Listing:
    defaults = {
        "title": "Cat Test",
        "category": ListingCategory.TUTORING,
        "status": ListingStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Listing.objects.create(**defaults)


class CategoriesViewTests(APITestCase):
    """Tests for GET /api/v1/categories/."""

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("v1:catalog:categories")

    def test_public_access_returns_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_returns_all_seven_categories(self):
        """All 7 ListingCategory values must appear in the response."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        keys = [item["key"] for item in response.data]
        for category in ALL_CATEGORIES:
            self.assertIn(category, keys, f"Category '{category}' missing from response")
        self.assertEqual(len(keys), len(ALL_CATEGORIES))

    def test_each_item_has_key_and_count(self):
        """Each category item must have 'key' and 'count' fields."""
        response = self.client.get(self.url)
        for item in response.data:
            self.assertIn("key", item)
            self.assertIn("count", item)

    def test_zero_count_categories_included(self):
        """Categories with no ACTIVE listings still appear with count=0."""
        # Create ACTIVE listings only for TUTORING
        make_listing(category=ListingCategory.TUTORING)

        response = self.client.get(self.url)
        counts = {item["key"]: item["count"] for item in response.data}

        self.assertEqual(counts["TUTORING"], 1)
        # All others should be 0 (assuming clean test DB state)
        for category in ALL_CATEGORIES:
            if category != "TUTORING":
                self.assertEqual(
                    counts[category],
                    0,
                    f"Expected count=0 for {category}, got {counts[category]}",
                )

    def test_only_active_listings_counted(self):
        """DRAFT, PENDING, REJECTED listings must NOT increment the count."""
        make_listing(category=ListingCategory.SCHOOLS, status=ListingStatus.ACTIVE)
        make_listing(category=ListingCategory.SCHOOLS, status=ListingStatus.DRAFT)
        make_listing(category=ListingCategory.SCHOOLS, status=ListingStatus.PENDING)
        make_listing(category=ListingCategory.SCHOOLS, status=ListingStatus.REJECTED)

        response = self.client.get(self.url)
        counts = {item["key"]: item["count"] for item in response.data}
        self.assertEqual(counts["SCHOOLS"], 1)

    def test_correct_count_multiple_active_in_category(self):
        """Multiple ACTIVE listings in the same category increment count correctly."""
        for i in range(3):
            make_listing(
                title=f"Activity {i}",
                category=ListingCategory.ACTIVITIES,
            )

        response = self.client.get(self.url)
        counts = {item["key"]: item["count"] for item in response.data}
        self.assertEqual(counts["ACTIVITIES"], 3)

    def test_counts_across_multiple_categories(self):
        """Counts are correct for multiple categories simultaneously."""
        make_listing(category=ListingCategory.NURSERIES)
        make_listing(category=ListingCategory.NURSERIES)
        make_listing(category=ListingCategory.ENTERTAINMENT)

        response = self.client.get(self.url)
        counts = {item["key"]: item["count"] for item in response.data}
        self.assertEqual(counts["NURSERIES"], 2)
        self.assertEqual(counts["ENTERTAINMENT"], 1)
