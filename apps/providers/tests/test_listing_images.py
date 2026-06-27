"""
Tests for the listing image sub-resource endpoints (Option C):

    POST   /api/v1/provider/listings/<id>/images/        — upload one or more
    DELETE /api/v1/provider/listings/<id>/images/<img>/  — remove one by id

Images are managed only through these endpoints — never via the listing
create/update body. Ownership is enforced: a provider can only touch images
on listings they own (404 otherwise, for information hiding).
"""

import uuid
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from knox.models import AuthToken
from rest_framework.test import APIClient, APITestCase

from apps.catalog.models import Listing, ListingCategory, ListingImage, ListingStatus
from apps.users.enums import UserRole
from apps.users.models import CustomUser, Role

# Patch the task where the service looks it up, so DELETE doesn't hit storage.
TASK = "apps.catalog.services.delete_storage_objects"


def make_user(roles=None, verified=True, email=None) -> CustomUser:
    roles = roles or [UserRole.MASTERCLASS]
    email = email or f"user_{uuid.uuid4().hex[:8]}@example.com"
    user = CustomUser.objects.create_user(
        email=email, password="TestPass123!", is_verified=verified
    )
    user.roles.add(*[Role.objects.get_or_create(name=n)[0] for n in roles])
    if hasattr(user, "_role_names_cache"):
        del user._role_names_cache
    return user


def auth_client(user: CustomUser) -> APIClient:
    client = APIClient()
    _, token = AuthToken.objects.create(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def make_listing(owner: CustomUser) -> Listing:
    return Listing.objects.create(
        title="Test Listing",
        category=ListingCategory.MASTERCLASSES,
        status=ListingStatus.ACTIVE,
        owner=owner,
    )


def images_url(listing_id) -> str:
    return f"/api/v1/provider/listings/{listing_id}/images/"


def _test_image(name: str = "test.png") -> SimpleUploadedFile:
    return SimpleUploadedFile(
        name,
        (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
            b"\x90wS\xde\x00\x00\x00\x0cIDAT\x08\x99c`\x00\x00\x00\x02"
            b"\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
        ),
        content_type="image/png",
    )


class ListingImageUploadTests(APITestCase):
    def test_upload_creates_rows_and_returns_ids(self):
        user = make_user()
        listing = make_listing(user)
        resp = auth_client(user).post(
            images_url(listing.id),
            {"images": [_test_image("one.png"), _test_image("two.png")]},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(len(resp.data), 2)
        # Each returned image carries an id + url + position.
        for item in resp.data:
            self.assertIn("id", item)
            self.assertIn("url", item)
        # Rows persisted under this listing, keyed under listings/<id>/.
        images = listing.images.all()
        self.assertEqual(images.count(), 2)
        for img in images:
            self.assertTrue(img.key.startswith(f"listings/{listing.id}/"))

    def test_upload_appends_positions(self):
        user = make_user()
        listing = make_listing(user)
        ListingImage.objects.create(
            listing=listing, key=f"listings/{listing.id}/existing.png", position=0
        )
        auth_client(user).post(
            images_url(listing.id),
            {"images": [_test_image("new.png")]},
            format="multipart",
        )
        positions = sorted(listing.images.values_list("position", flat=True))
        self.assertEqual(positions, [0, 1])

    def test_upload_to_foreign_listing_is_404(self):
        owner = make_user()
        other = make_user()
        listing = make_listing(owner)
        resp = auth_client(other).post(
            images_url(listing.id),
            {"images": [_test_image()]},
            format="multipart",
        )
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(listing.images.count(), 0)

    def test_upload_requires_auth(self):
        user = make_user()
        listing = make_listing(user)
        resp = APIClient().post(
            images_url(listing.id),
            {"images": [_test_image()]},
            format="multipart",
        )
        self.assertIn(resp.status_code, (401, 403))


class ListingImageDeleteTests(APITestCase):
    def _detail_url(self, listing_id, image_id) -> str:
        return f"/api/v1/provider/listings/{listing_id}/images/{image_id}/"

    def test_delete_removes_row_and_enqueues_cleanup(self):
        user = make_user()
        listing = make_listing(user)
        image = ListingImage.objects.create(
            listing=listing, key=f"listings/{listing.id}/a.png", position=0
        )
        with patch(TASK) as task:
            with self.captureOnCommitCallbacks(execute=True):
                resp = auth_client(user).delete(
                    self._detail_url(listing.id, image.id)
                )
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(ListingImage.objects.filter(id=image.id).exists())
        task.delay.assert_called_once_with([f"listings/{listing.id}/a.png"])

    def test_delete_foreign_listing_image_is_404(self):
        owner = make_user()
        other = make_user()
        listing = make_listing(owner)
        image = ListingImage.objects.create(
            listing=listing, key=f"listings/{listing.id}/a.png", position=0
        )
        resp = auth_client(other).delete(self._detail_url(listing.id, image.id))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(ListingImage.objects.filter(id=image.id).exists())

    def test_delete_unknown_image_is_404(self):
        user = make_user()
        listing = make_listing(user)
        resp = auth_client(user).delete(self._detail_url(listing.id, uuid.uuid4()))
        self.assertEqual(resp.status_code, 404)