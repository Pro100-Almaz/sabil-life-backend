"""
Tests for MinIO image cleanup on Listing delete/update.

Two layers:
  1. url_to_storage_key() — pure unit tests for the URL -> storage-key reversal.
  2. Signals — pre_delete deletes all images; pre_save deletes only the
     URLs removed from image_urls. We patch the Celery task and assert which
     keys get enqueued, so no real storage is touched.

The on_commit callbacks only fire when the transaction commits, so the signal
tests use the `django_capture_on_commit_callbacks` fixture with execute=True.
"""

from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.catalog.services import url_to_storage_key

# Patch the name as imported into the signals module's namespace, not where
# the task is defined — that's the reference the on_commit lambda resolves.
TASK = "apps.catalog.signals.delete_storage_objects"


def make_listing(**kwargs) -> Listing:
    defaults = {
        "title": "Test Listing",
        "category": ListingCategory.MASTERCLASSES,
        "status": ListingStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Listing.objects.create(**defaults)


# ---------------------------------------------------------------------------
# 1. url_to_storage_key — pure function, no DB
# ---------------------------------------------------------------------------
class TestUrlToStorageKey:
    def test_local_absolute_url(self):
        url = "http://testserver/media/listings/abc/img.jpg"
        assert url_to_storage_key(url) == "listings/abc/img.jpg"

    def test_local_relative_url(self):
        # default_storage.url() can return a path-only URL when not absolutized.
        assert url_to_storage_key("/media/listings/abc/img.jpg") == "listings/abc/img.jpg"

    @override_settings(MEDIA_URL="https://minio.local/sabil-bucket/")
    def test_minio_url_strips_endpoint_and_bucket(self):
        url = "https://minio.local/sabil-bucket/listings/abc/img.jpg"
        assert url_to_storage_key(url) == "listings/abc/img.jpg"

    @override_settings(MEDIA_URL="https://minio.local/sabil-bucket/")
    def test_minio_url_with_querystring_auth(self):
        # AWS_QUERYSTRING_AUTH=True appends ?X-Amz-... — must be dropped.
        url = "https://minio.local/sabil-bucket/listings/abc/img.jpg?X-Amz-Signature=deadbeef"
        assert url_to_storage_key(url) == "listings/abc/img.jpg"

    def test_url_encoded_path_is_decoded(self):
        url = "http://testserver/media/listings/abc/my%20file.jpg"
        assert url_to_storage_key(url) == "listings/abc/my file.jpg"

    @pytest.mark.parametrize("value", ["", None])
    def test_empty_returns_none(self, value):
        assert url_to_storage_key(value) is None

    def test_round_trip_with_default_storage(self):
        """The contract: url_to_storage_key(default_storage.url(name)) == name."""
        from django.core.files.storage import default_storage

        name = "listings/abc/round-trip.jpg"
        assert url_to_storage_key(default_storage.url(name)) == name


# ---------------------------------------------------------------------------
# 2. Signals — which keys get enqueued on delete/update
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestImageCleanupSignals:
    def test_delete_enqueues_all_keys(self, django_capture_on_commit_callbacks):
        listing = make_listing(
            image_urls=[
                "/media/listings/a/one.jpg",
                "/media/listings/a/two.jpg",
            ]
        )
        with patch(TASK) as task:
            with django_capture_on_commit_callbacks(execute=True):
                listing.delete()

        task.delay.assert_called_once()
        (keys,) = task.delay.call_args.args
        assert set(keys) == {"listings/a/one.jpg", "listings/a/two.jpg"}

    def test_update_removing_url_enqueues_only_removed(
        self, django_capture_on_commit_callbacks
    ):
        listing = make_listing(
            image_urls=[
                "/media/listings/a/keep.jpg",
                "/media/listings/a/drop.jpg",
            ]
        )
        with patch(TASK) as task:
            with django_capture_on_commit_callbacks(execute=True):
                listing.image_urls = ["/media/listings/a/keep.jpg"]
                listing.save()

        task.delay.assert_called_once()
        (keys,) = task.delay.call_args.args
        assert keys == ["listings/a/drop.jpg"]

    def test_update_appending_url_does_not_enqueue(
        self, django_capture_on_commit_callbacks
    ):
        """The append flow from _store_uploaded_images must never delete."""
        listing = make_listing(image_urls=["/media/listings/a/one.jpg"])
        with patch(TASK) as task:
            with django_capture_on_commit_callbacks(execute=True):
                listing.image_urls = [
                    "/media/listings/a/one.jpg",
                    "/media/listings/a/new.jpg",
                ]
                listing.save()

        task.delay.assert_not_called()

    def test_create_does_not_enqueue(self, django_capture_on_commit_callbacks):
        with patch(TASK) as task:
            with django_capture_on_commit_callbacks(execute=True):
                make_listing(image_urls=["/media/listings/a/one.jpg"])

        task.delay.assert_not_called()

    def test_update_unrelated_field_does_not_enqueue(
        self, django_capture_on_commit_callbacks
    ):
        listing = make_listing(image_urls=["/media/listings/a/one.jpg"])
        with patch(TASK) as task:
            with django_capture_on_commit_callbacks(execute=True):
                listing.title = "Renamed"
                listing.save()

        task.delay.assert_not_called()