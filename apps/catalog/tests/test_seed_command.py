"""
Tests for the seed_catalog management command.

Image seeding is network-backed in production (picsum.photos), so every test
here patches ``_fetch_image`` / ``default_storage.save`` to keep runs
deterministic and offline. Tests that care about images opt in explicitly.
"""

import uuid
from collections import Counter
from io import StringIO
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command

from apps.catalog.management.commands import seed_catalog
from apps.catalog.management.commands.seed_catalog import (
    LISTINGS,
    NAMESPACE,
    _EXPECTED_TOTALS,
    _uid,
)
from apps.catalog.models import Listing, ListingCategory, ListingImage, ListingStatus

User = get_user_model()

pytestmark = pytest.mark.django_db

# Where the command module resolves these names — patch here, not at source.
FETCH = "apps.catalog.management.commands.seed_catalog._fetch_image"
STORAGE = "apps.catalog.management.commands.seed_catalog.default_storage"
# delete_listing() enqueues storage cleanup via this reference in services.
CLEANUP_TASK = "apps.catalog.services.delete_storage_objects"


def seed(stdout=None, **kwargs):
    out = stdout or StringIO()
    # Default: no images (network unavailable) unless a test overrides FETCH.
    with patch(FETCH, return_value=None):
        call_command("seed_catalog", stdout=out, **kwargs)
    return out


# ---------------------------------------------------------------------------
# Import-time sanity checks
# ---------------------------------------------------------------------------


class TestSeedDataIntegrity:
    def test_dataset_length_matches_expected_totals(self):
        assert len(LISTINGS) == sum(_EXPECTED_TOTALS.values())

    def test_category_distribution_matches_expected(self):
        actual = Counter(d["category"] for d in LISTINGS)
        assert actual == _EXPECTED_TOTALS

    def test_slugs_are_unique(self):
        slugs = [d["slug"] for d in LISTINGS]
        assert len(slugs) == len(set(slugs))


# ---------------------------------------------------------------------------
# Core behaviour
# ---------------------------------------------------------------------------


class TestSeedCatalogCreates:
    def test_creates_all_listings(self):
        seed()
        assert Listing.objects.count() == len(LISTINGS)

    def test_correct_category_distribution(self):
        seed()
        counts = Counter(Listing.objects.values_list("category", flat=True))
        for category, expected in _EXPECTED_TOTALS.items():
            assert counts[category] == expected

    def test_all_listings_are_active(self):
        seed()
        assert Listing.objects.exclude(status=ListingStatus.ACTIVE).count() == 0

    def test_owner_assignment(self):
        seed()
        # Only TUTORING + MASTERCLASSES carry a provider owner.
        owned = _EXPECTED_TOTALS[ListingCategory.TUTORING] + _EXPECTED_TOTALS[
            ListingCategory.MASTERCLASSES
        ]
        assert Listing.objects.filter(owner__isnull=False).count() == owned
        assert Listing.objects.filter(owner__isnull=True).count() == (
            len(LISTINGS) - owned
        )


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestSeedCatalogIdempotency:
    def test_second_run_creates_zero_new_listings(self):
        seed()
        assert Listing.objects.count() == len(LISTINGS)
        out = seed()
        assert Listing.objects.count() == len(LISTINGS)
        assert "0 created" in out.getvalue()

    def test_deterministic_uuid_stability(self):
        slug = LISTINGS[0]["slug"]
        assert _uid(slug) == uuid.uuid5(NAMESPACE, slug)

    def test_listing_ids_match_deterministic_uuids(self):
        seed()
        for data in LISTINGS:
            assert Listing.objects.filter(id=_uid(data["slug"])).exists()


# ---------------------------------------------------------------------------
# --count flag
# ---------------------------------------------------------------------------


class TestSeedCatalogCount:
    def test_count_no_writes(self):
        out = seed(count=True)
        assert Listing.objects.count() == 0
        assert f"Would insert: {len(LISTINGS)}" in out.getvalue()

    def test_count_after_seed(self):
        seed()
        out = seed(count=True)
        assert "Would insert: 0" in out.getvalue()


# ---------------------------------------------------------------------------
# --clean flag
# ---------------------------------------------------------------------------


class TestSeedCatalogClean:
    def test_clean_reseeds_to_full_set(self):
        seed()
        seed(clean=True)
        assert Listing.objects.count() == len(LISTINGS)

    def test_clean_does_not_touch_provider_owned_listings(self):
        provider = User.objects.create_user(
            email="provider@example.com", password="testpass123"
        )
        provider_listing = Listing.objects.create(
            title="Provider Listing",
            category=ListingCategory.TUTORING,
            status=ListingStatus.ACTIVE,
            owner=provider,
        )
        seed()
        seed(clean=True)
        assert Listing.objects.count() == len(LISTINGS) + 1
        assert Listing.objects.filter(id=provider_listing.id).exists()


# ---------------------------------------------------------------------------
# Images — backfill + storage-cleanup on --clean
# ---------------------------------------------------------------------------


class TestSeedCatalogImages:
    def _content(self, *args, **kwargs):
        return ContentFile(b"fake-image-bytes")

    def test_offline_first_run_then_online_backfill(self):
        # First run offline: no images fetched.
        seed()
        assert ListingImage.objects.count() == 0

        # Later run with network + storage available: images get backfilled
        # even though the listings already exist (update_or_create -> created
        # is False), because they currently have zero images.
        out = StringIO()
        with patch(FETCH, side_effect=self._content), patch(STORAGE) as storage:
            storage.save.side_effect = lambda name, content: name
            call_command("seed_catalog", stdout=out)

        assert "0 created" in out.getvalue()  # no new listings
        assert ListingImage.objects.count() > 0  # but images now present

    def test_backfill_is_idempotent(self):
        with patch(FETCH, side_effect=self._content), patch(STORAGE) as storage:
            storage.save.side_effect = lambda name, content: name
            call_command("seed_catalog", stdout=StringIO())
            first = ListingImage.objects.count()
            # Re-run: listings already have images, so none are added.
            call_command("seed_catalog", stdout=StringIO())
            assert ListingImage.objects.count() == first

    def test_clean_enqueues_image_storage_cleanup(
        self, django_capture_on_commit_callbacks
    ):
        # Seed with images present.
        with patch(FETCH, side_effect=self._content), patch(STORAGE) as storage:
            storage.save.side_effect = lambda name, content: name
            call_command("seed_catalog", stdout=StringIO())

        keys = set(ListingImage.objects.values_list("key", flat=True))
        assert keys  # sanity: there are images to clean up

        # --clean must route through delete_listing() so the storage keys are
        # enqueued (a bulk queryset delete would orphan them).
        with patch(CLEANUP_TASK) as task:
            with django_capture_on_commit_callbacks(execute=True):
                seed(clean=True)
            enqueued = set()
            for call in task.delay.call_args_list:
                (batch,) = call.args
                enqueued.update(batch)

        assert keys <= enqueued
