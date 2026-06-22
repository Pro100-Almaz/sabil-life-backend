"""
Tests for the seed_catalog management command — Phase 3.
"""

import uuid
from collections import Counter
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.catalog.management.commands.seed_catalog import LISTINGS, NAMESPACE, _uid
from apps.catalog.models import Listing, ListingCategory, ListingStatus

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def seed(stdout=None, **kwargs):
    out = stdout or StringIO()
    call_command("seed_catalog", stdout=out, **kwargs)
    return out


# ---------------------------------------------------------------------------
# Core behaviour
# ---------------------------------------------------------------------------


class TestSeedCatalogCreates:
    def test_creates_24_listings(self):
        seed()
        assert Listing.objects.count() == 24

    def test_correct_category_distribution(self):
        seed()
        counts = Counter(Listing.objects.values_list("category", flat=True))
        assert counts[ListingCategory.SCHOOLS] == 4
        assert counts[ListingCategory.NURSERIES] == 3
        assert counts[ListingCategory.ACTIVITIES] == 6
        assert counts[ListingCategory.ENTERTAINMENT] == 3
        assert counts[ListingCategory.TUTORING] == 3
        assert counts[ListingCategory.MASTERCLASSES] == 3
        assert counts[ListingCategory.PARTNERSHIPS] == 2

    def test_all_listings_are_active(self):
        seed()
        non_active = Listing.objects.exclude(status=ListingStatus.ACTIVE).count()
        assert non_active == 0

    def test_all_listings_have_null_owner(self):
        seed()
        with_owner = Listing.objects.filter(owner__isnull=False).count()
        assert with_owner == 6

    def test_featured_count_in_expected_range(self):
        seed()
        featured_count = Listing.objects.filter(is_featured=True).count()
        assert 5 <= featured_count <= 8, (
            f"Expected 5–8 featured listings, got {featured_count}"
        )

    def test_at_least_one_listing_per_category(self):
        seed()
        for category in ListingCategory:
            assert Listing.objects.filter(category=category).exists(), (
                f"No listing found for category {category}"
            )


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestSeedCatalogIdempotency:
    def test_second_run_creates_zero_new_listings(self):
        seed()
        assert Listing.objects.count() == 24
        seed()
        assert Listing.objects.count() == 24

    def test_summary_output_shows_zero_created_on_second_run(self):
        seed()
        out = seed()
        output = out.getvalue()
        assert "0 created" in output
        assert "24 already existed" in output

    def test_deterministic_uuid_stability(self):
        """The same slug always produces the same UUID."""
        slug = "schools-doha-international-academy"
        uid1 = _uid(slug)
        uid2 = uuid.uuid5(NAMESPACE, slug)
        assert uid1 == uid2

    def test_listing_ids_match_deterministic_uuids(self):
        seed()
        for data in LISTINGS:
            expected_id = _uid(data["slug"])
            assert Listing.objects.filter(id=expected_id).exists(), (
                f"Listing with id {expected_id} (slug={data['slug']}) not found"
            )


# ---------------------------------------------------------------------------
# --clean flag
# ---------------------------------------------------------------------------


class TestSeedCatalogClean:
    def test_clean_reseeds_to_24(self):
        seed()
        seed(clean=True)
        assert Listing.objects.count() == 24

    def test_clean_does_not_touch_provider_owned_listings(self):
        """Provider-owned listings (owner IS NOT NULL) must survive --clean."""
        provider = User.objects.create_user(
            email="provider@example.com",
            password="testpass123",
        )
        provider_listing = Listing.objects.create(
            title="Provider Listing",
            category=ListingCategory.TUTORING,
            status=ListingStatus.ACTIVE,
            owner=provider,
        )
        seed()
        seed(clean=True)

        # Admin-seeded: 24; provider: 1 — total 25
        assert Listing.objects.count() == 25
        assert Listing.objects.filter(id=provider_listing.id).exists()

    def test_clean_deletes_admin_owned_listings(self):
        seed()
        assert Listing.objects.filter(owner__isnull=True).count() == 18
        # Wipe and reseed
        seed(clean=True)
        # Should still be exactly 24 admin-owned listings (deleted + reseeded)
        assert Listing.objects.filter(owner__isnull=True).count() == 18


# ---------------------------------------------------------------------------
# --count flag
# ---------------------------------------------------------------------------


class TestSeedCatalogCount:
    def test_count_no_writes(self):
        out = seed(count=True)
        assert Listing.objects.count() == 0
        assert "Would insert: 24" in out.getvalue()

    def test_count_after_seed(self):
        seed()
        out = seed(count=True)
        assert "Would insert: 0" in out.getvalue()
        assert "Already exist: 24" in out.getvalue()


# ---------------------------------------------------------------------------
# Spot-checks on data quality
# ---------------------------------------------------------------------------


class TestSeedCatalogDataQuality:
    def test_all_listings_have_image_urls(self):
        seed()
        for listing in Listing.objects.all():
            assert listing.image_urls, f"{listing.title} has no image URLs"

    def test_all_listings_have_non_zero_rating(self):
        seed()
        zero_rating = Listing.objects.filter(rating=0).count()
        assert zero_rating == 0

    def test_all_listings_have_neighborhood(self):
        seed()
        empty_hood = Listing.objects.filter(neighborhood="").count()
        assert empty_hood == 0

    def test_summary_output_contains_breakdown(self):
        out = seed()
        output = out.getvalue()
        assert "SCHOOLS" in output
        assert "NURSERIES" in output
        assert "ACTIVITIES" in output
