import uuid
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from knox.models import AuthToken
from rest_framework.test import APIClient, APITestCase

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.users.enums import UserRole
from apps.users.models import CustomUser, Role

LISTINGS_URL = "/api/v1/provider/listings/"
PUBLIC_LISTINGS_URL = "/api/v1/listings/"


def make_user(
    roles: list[str] | None = None,
    verified: bool = True,
    email: str | None = None,
) -> CustomUser:
    roles = roles or [UserRole.MASTERCLASS]
    email = email or f"user_{uuid.uuid4().hex[:8]}@example.com"
    user = CustomUser.objects.create_user(
        email=email,
        password="TestPass123!",
        is_verified=verified,
    )
    role_objs = [Role.objects.get_or_create(name=name)[0] for name in roles]
    user.roles.add(*role_objs)
    if hasattr(user, "_role_names_cache"):
        del user._role_names_cache
    return user


def auth_client(user: CustomUser) -> APIClient:
    client = APIClient()
    _, token = AuthToken.objects.create(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def _listing_payload(**kwargs) -> dict:
    defaults = {
        "title": "Test Masterclass",
        "category": ListingCategory.MASTERCLASSES,
        "subtitle": "Expert pottery",
        "neighborhood": "West Bay",
        "price_from_qar": 100,
        "description": "Great masterclass.",
    }
    defaults.update(kwargs)
    return defaults


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


class ProviderListingCreateTests(APITestCase):
    def test_verified_masterclass_creates_masterclasses_listing(self):
        user = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        client = auth_client(user)
        resp = client.post(LISTINGS_URL, _listing_payload(), format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["status"], ListingStatus.PENDING)
        self.assertEqual(resp.data["owner_id"], str(user.id))
        self.assertEqual(resp.data["category"], ListingCategory.MASTERCLASSES)

    def test_masterclass_cannot_create_tutoring_listing(self):
        user = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        client = auth_client(user)
        resp = client.post(
            LISTINGS_URL,
            _listing_payload(category=ListingCategory.TUTORING),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("category", resp.data)

    def test_masterclass_cannot_create_schools_listing(self):
        user = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        client = auth_client(user)
        resp = client.post(
            LISTINGS_URL,
            _listing_payload(category=ListingCategory.SCHOOLS),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("category", resp.data)

    def test_tutor_cannot_create_listing(self):
        user = make_user(roles=[UserRole.TUTOR], verified=True)
        client = auth_client(user)
        resp = client.post(
            LISTINGS_URL,
            _listing_payload(category=ListingCategory.TUTORING),
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_admin_creates_listing_in_any_category(self):
        user = make_user(roles=[UserRole.ADMIN], verified=True)
        client = auth_client(user)
        resp = client.post(
            LISTINGS_URL,
            _listing_payload(category=ListingCategory.TUTORING),
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["category"], ListingCategory.TUTORING)
        self.assertEqual(resp.data["owner_id"], str(user.id))

    def test_manager_creates_listing(self):
        user = make_user(roles=[UserRole.MANAGER], verified=True)
        client = auth_client(user)
        resp = client.post(LISTINGS_URL, _listing_payload(), format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["category"], ListingCategory.MASTERCLASSES)

    def test_unverified_masterclass_creates_with_draft_status(self):
        user = make_user(roles=[UserRole.MASTERCLASS], verified=False)
        client = auth_client(user)
        resp = client.post(LISTINGS_URL, _listing_payload(), format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["status"], ListingStatus.DRAFT)

    def test_status_in_body_is_ignored(self):
        """Any status value in the request body must be overridden by the server."""
        user = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        client = auth_client(user)
        payload = _listing_payload()
        payload["status"] = ListingStatus.ACTIVE
        resp = client.post(LISTINGS_URL, payload, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["status"], ListingStatus.PENDING)

    def test_owner_in_body_is_ignored(self):
        """Any owner value in the body must be discarded; owner = caller."""
        user1 = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        user2 = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        client = auth_client(user1)
        payload = _listing_payload()
        payload["owner"] = user2.id
        resp = client.post(LISTINGS_URL, payload, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["owner_id"], str(user1.id))

    def test_family_cannot_create_listing(self):
        user = make_user(roles=[UserRole.FAMILY], verified=True)
        client = auth_client(user)
        resp = client.post(LISTINGS_URL, _listing_payload(), format="json")
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_cannot_create_listing(self):
        client = APIClient()
        resp = client.post(LISTINGS_URL, _listing_payload(), format="json")
        self.assertEqual(resp.status_code, 401)

    @patch("apps.providers.serializers.default_storage.url")
    @patch("apps.providers.serializers.default_storage.save")
    def test_masterclass_can_create_listing_with_uploaded_images(
        self,
        mock_save,
        mock_url,
    ):
        user = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        client = auth_client(user)
        mock_save.side_effect = [
            "listings/first.png",
            "listings/second.png",
        ]
        mock_url.side_effect = [
            "https://minio.test/sabil-life-media/listings/first.png",
            "https://minio.test/sabil-life-media/listings/second.png",
        ]

        resp = client.post(
            LISTINGS_URL,
            {
                **_listing_payload(),
                "images": [_test_image("one.png"), _test_image("two.png")],
            },
            format="multipart",
        )

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["status"], ListingStatus.PENDING)
        self.assertEqual(
            resp.data["image_urls"],
            [
                "https://minio.test/sabil-life-media/listings/first.png",
                "https://minio.test/sabil-life-media/listings/second.png",
            ],
        )
        listing = Listing.objects.get(id=resp.data["id"])
        self.assertEqual(listing.image_urls, resp.data["image_urls"])


class ProviderListingListTests(APITestCase):
    def test_provider_sees_only_own_listings(self):
        user1 = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        user2 = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        Listing.objects.create(
            title="Listing A",
            category=ListingCategory.MASTERCLASSES,
            owner=user1,
            status=ListingStatus.PENDING,
        )
        Listing.objects.create(
            title="Listing B",
            category=ListingCategory.MASTERCLASSES,
            owner=user2,
            status=ListingStatus.PENDING,
        )
        client = auth_client(user1)
        resp = client.get(LISTINGS_URL)
        self.assertEqual(resp.status_code, 200)
        titles = [item["title"] for item in resp.data["results"]]
        self.assertIn("Listing A", titles)
        self.assertNotIn("Listing B", titles)


class ProviderListingRetrieveTests(APITestCase):
    def test_masterclass_can_get_own_listing(self):
        user = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        listing = Listing.objects.create(
            title="Own Listing",
            category=ListingCategory.MASTERCLASSES,
            owner=user,
            status=ListingStatus.PENDING,
        )
        client = auth_client(user)
        resp = client.get(f"{LISTINGS_URL}{listing.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["title"], "Own Listing")

    def test_get_other_listing_returns_404(self):
        user1 = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        user2 = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        listing = Listing.objects.create(
            title="Other Listing",
            category=ListingCategory.MASTERCLASSES,
            owner=user2,
            status=ListingStatus.PENDING,
        )
        client = auth_client(user1)
        resp = client.get(f"{LISTINGS_URL}{listing.id}/")
        self.assertEqual(resp.status_code, 404)


class ProviderListingUpdateTests(APITestCase):
    def test_masterclass_patch_own_listing(self):
        user = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        listing = Listing.objects.create(
            title="Old Title",
            category=ListingCategory.MASTERCLASSES,
            owner=user,
            status=ListingStatus.DRAFT,
        )
        client = auth_client(user)
        resp = client.patch(
            f"{LISTINGS_URL}{listing.id}/",
            {"title": "New Title"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["title"], "New Title")
        # Verified user → status flips to PENDING
        self.assertEqual(resp.data["status"], ListingStatus.PENDING)

    def test_unverified_masterclass_patch_stays_draft(self):
        user = make_user(roles=[UserRole.MASTERCLASS], verified=False)
        listing = Listing.objects.create(
            title="Draft",
            category=ListingCategory.MASTERCLASSES,
            owner=user,
            status=ListingStatus.DRAFT,
        )
        client = auth_client(user)
        resp = client.patch(
            f"{LISTINGS_URL}{listing.id}/",
            {"title": "Updated Draft"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["status"], ListingStatus.DRAFT)

    def test_patch_category_to_wrong_value_returns_400(self):
        user = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        listing = Listing.objects.create(
            title="Masterclass Listing",
            category=ListingCategory.MASTERCLASSES,
            owner=user,
            status=ListingStatus.PENDING,
        )
        client = auth_client(user)
        resp = client.patch(
            f"{LISTINGS_URL}{listing.id}/",
            {"category": ListingCategory.TUTORING},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("category", resp.data)

    @patch("apps.providers.serializers.default_storage.url")
    @patch("apps.providers.serializers.default_storage.save")
    def test_patch_can_append_uploaded_images(
        self,
        mock_save,
        mock_url,
    ):
        user = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        listing = Listing.objects.create(
            title="With Existing Image",
            category=ListingCategory.MASTERCLASSES,
            owner=user,
            status=ListingStatus.DRAFT,
            image_urls=["https://existing.example/cover.png"],
        )
        client = auth_client(user)
        mock_save.return_value = "listings/third.png"
        mock_url.return_value = "https://minio.test/sabil-life-media/listings/third.png"

        resp = client.patch(
            f"{LISTINGS_URL}{listing.id}/",
            {"images": [_test_image("third.png")]},
            format="multipart",
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.data["image_urls"],
            [
                "https://existing.example/cover.png",
                "https://minio.test/sabil-life-media/listings/third.png",
            ],
        )
        self.assertEqual(resp.data["status"], ListingStatus.PENDING)

    def test_patch_another_listing_returns_404(self):
        user1 = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        user2 = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        listing = Listing.objects.create(
            title="Other",
            category=ListingCategory.MASTERCLASSES,
            owner=user2,
            status=ListingStatus.PENDING,
        )
        client = auth_client(user1)
        resp = client.patch(
            f"{LISTINGS_URL}{listing.id}/",
            {"title": "Hacked"},
            format="json",
        )
        self.assertEqual(resp.status_code, 404)


class ProviderListingDeleteTests(APITestCase):
    def test_masterclass_delete_own_listing(self):
        user = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        listing = Listing.objects.create(
            title="To Delete",
            category=ListingCategory.MASTERCLASSES,
            owner=user,
            status=ListingStatus.PENDING,
        )
        client = auth_client(user)
        resp = client.delete(f"{LISTINGS_URL}{listing.id}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Listing.objects.filter(id=listing.id).exists())

    def test_delete_another_listing_returns_404(self):
        user1 = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        user2 = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        listing = Listing.objects.create(
            title="Not Mine",
            category=ListingCategory.MASTERCLASSES,
            owner=user2,
            status=ListingStatus.PENDING,
        )
        client = auth_client(user1)
        resp = client.delete(f"{LISTINGS_URL}{listing.id}/")
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Listing.objects.filter(id=listing.id).exists())


class ProviderListingPublicVisibilityTests(APITestCase):
    def test_pending_listing_not_visible_in_public_api(self):
        user = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        client = auth_client(user)
        resp = client.post(LISTINGS_URL, _listing_payload(title="Hidden"), format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["status"], ListingStatus.PENDING)

        public = APIClient()
        pub_resp = public.get(PUBLIC_LISTINGS_URL)
        self.assertEqual(pub_resp.status_code, 200)
        titles = [item["title"] for item in pub_resp.data["results"]]
        self.assertNotIn("Hidden", titles)

    def test_active_listing_visible_in_public_api_after_admin_approval(self):
        user = make_user(roles=[UserRole.MASTERCLASS], verified=True)
        listing = Listing.objects.create(
            title="Approved Listing",
            category=ListingCategory.MASTERCLASSES,
            owner=user,
            status=ListingStatus.PENDING,
        )
        # Simulate admin running approve_listings
        Listing.objects.filter(id=listing.id).update(status=ListingStatus.ACTIVE)

        public = APIClient()
        pub_resp = public.get(PUBLIC_LISTINGS_URL)
        self.assertEqual(pub_resp.status_code, 200)
        titles = [item["title"] for item in pub_resp.data["results"]]
        self.assertIn("Approved Listing", titles)
