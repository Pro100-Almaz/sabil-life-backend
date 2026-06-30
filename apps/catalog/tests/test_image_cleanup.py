"""
Tests for MinIO image cleanup (Option C — images as a ListingImage relation).

Two layers:
  1. url_to_storage_key() — pure unit tests for the URL -> storage-key reversal.
     The helper is retained only for the data-migration backfill; runtime
     cleanup no longer parses URLs (it deletes by stored key).
  2. Service layer — delete_listing_image() enqueues the image's key;
     delete_listing() collects every child image's key and enqueues them as a
     single batch. We patch the Celery task and assert which keys get enqueued,
     so no real storage is touched. (Storage cleanup is explicit in the service
     layer — there is no longer a post_delete signal.)

The on_commit callbacks only fire when the transaction commits, so the service
tests use the `django_capture_on_commit_callbacks` fixture with execute=True.
"""

from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.catalog.models import (
    Listing,
    ListingCategory,
    ListingImage,
    ListingStatus,
)
from apps.catalog.services import (
    delete_listing,
    delete_listing_image,
    url_to_storage_key,
)

# Patch the name as imported into the services module's namespace, not where
# the task is defined — that's the reference the on_commit lambda resolves.
TASK = "apps.catalog.services.delete_storage_objects"


def make_listing(**kwargs) -> Listing:
    defaults = {
        "title": "Test Listing",
        "category": ListingCategory.MASTERCLASSES,
        "status": ListingStatus.ACTIVE,
    }
    defaults.update(kwargs)
    return Listing.objects.create(**defaults)


def make_image(listing: Listing, key: str, position: int = 0) -> ListingImage:
    return ListingImage.objects.create(listing=listing, key=key, position=position)


def _enqueued_keys(task) -> set[str]:
    """Flatten every key passed across all task.delay([...]) calls."""
    keys: set[str] = set()
    for call in task.delay.call_args_list:
        (batch,) = call.args
        keys.update(batch)
    return keys


# ---------------------------------------------------------------------------
# 1. url_to_storage_key — pure function, no DB (used by the backfill migration)
# ---------------------------------------------------------------------------
class TestUrlToStorageKey:
    @override_settings(MEDIA_URL = "/media/")
    def test_local_absolute_url(self):
        url = "http://testserver/media/listings/abc/img.jpg"
        assert url_to_storage_key(url) == "listings/abc/img.jpg"

    @override_settings(MEDIA_URL = "/media/")
    def test_local_relative_url(self):
        assert url_to_storage_key("/media/listings/abc/img.jpg") == "listings/abc/img.jpg"

    @override_settings(MEDIA_URL="https://minio.local/sabil-bucket/")
    def test_minio_url_strips_endpoint_and_bucket(self):
        url = "https://minio.local/sabil-bucket/listings/abc/img.jpg"
        assert url_to_storage_key(url) == "listings/abc/img.jpg"

    @override_settings(MEDIA_URL="https://minio.local/sabil-bucket/")
    def test_minio_url_with_querystring_auth(self):
        url = "https://minio.local/sabil-bucket/listings/abc/img.jpg?X-Amz-Signature=deadbeef"
        assert url_to_storage_key(url) == "listings/abc/img.jpg"

    @override_settings(MEDIA_URL = "/media/")
    def test_url_encoded_path_is_decoded(self):
        url = "http://testserver/media/listings/abc/my%20file.jpg"
        assert url_to_storage_key(url) == "listings/abc/my file.jpg"

    @pytest.mark.parametrize("value", ["", None])
    def test_empty_returns_none(self, value):
        assert url_to_storage_key(value) is None


# ---------------------------------------------------------------------------
# 2. Service layer — which keys get enqueued on image / listing delete
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestImageCleanupServices:
    def test_delete_listing_image_enqueues_its_key(
        self, django_capture_on_commit_callbacks
    ):
        listing = make_listing()
        image = make_image(listing, "listings/a/one.jpg")
        with patch(TASK) as task:
            with django_capture_on_commit_callbacks(execute=True):
                delete_listing_image(image)

        task.delay.assert_called_once_with(["listings/a/one.jpg"])
        assert not ListingImage.objects.filter(pk=image.pk).exists()

    def test_delete_listing_enqueues_all_image_keys_in_one_batch(
        self, django_capture_on_commit_callbacks
    ):
        listing = make_listing()
        make_image(listing, "listings/a/one.jpg", position=0)
        make_image(listing, "listings/a/two.jpg", position=1)
        with patch(TASK) as task:
            with django_capture_on_commit_callbacks(execute=True):
                delete_listing(listing)

        # All of the listing's image keys are enqueued in a single batch.
        assert task.delay.call_count == 1
        assert _enqueued_keys(task) == {"listings/a/one.jpg", "listings/a/two.jpg"}
        assert not Listing.objects.filter(pk=listing.pk).exists()

    def test_delete_listing_with_no_images_enqueues_nothing(
        self, django_capture_on_commit_callbacks
    ):
        listing = make_listing()
        with patch(TASK) as task:
            with django_capture_on_commit_callbacks(execute=True):
                delete_listing(listing)

        task.delay.assert_not_called()

    def test_delete_listing_image_with_blank_key_enqueues_nothing(
        self, django_capture_on_commit_callbacks
    ):
        listing = make_listing()
        image = make_image(listing, "")
        with patch(TASK) as task:
            with django_capture_on_commit_callbacks(execute=True):
                delete_listing_image(image)

        task.delay.assert_not_called()