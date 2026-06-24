import uuid

from knox.models import AuthToken
from rest_framework.test import APIClient, APITestCase

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.users.enums import UserRole
from apps.users.models import CustomUser

LISTINGS_URL = "/api/v1/provider/listings/"
PUBLIC_LISTINGS_URL = "/api/v1/listings/"


def make_user(
    role: str = UserRole.TUTOR,
    verified: bool = True,
    email: str | None = None,
) -> CustomUser:
    email = email or f"{role.lower()}_{uuid.uuid4().hex[:8]}@example.com"
    return CustomUser.objects.create_user(
        email=email,
        password="TestPass123!",
        role=role,
        is_verified=verified,
    )


def auth_client(user: CustomUser) -> APIClient:
    client = APIClient()
    _, token = AuthToken.objects.create(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def _listing_payload(**kwargs) -> dict:
    defaults = {
        "title": "Test Tutoring",
        "category": ListingCategory.TUTORING,
        "subtitle": "Expert maths",
        "neighborhood": "West Bay",
        "price_from_qar": 100,
        "description": "Great tutor.",
    }
    defaults.update(kwargs)
    return defaults


class ProviderListingCreateTests(APITestCase):
    def test_verified_tutor_creates_tutoring_listing(self):
        user = make_user(role=UserRole.TUTOR, verified=True)
        client = auth_client(user)
        resp = client.post(LISTINGS_URL, _listing_payload(), format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["status"], ListingStatus.PENDING)
        self.assertEqual(resp.data["owner_id"], str(user.id))
        self.assertEqual(resp.data["category"], ListingCategory.TUTORING)

    def test_verified_tutor_cannot_create_masterclasses_listing(self):
        user = make_user(role=UserRole.TUTOR, verified=True)
        client = auth_client(user)
        resp = client.post(
            LISTINGS_URL,
            _listing_payload(category=ListingCategory.MASTERCLASSES),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("category", resp.data)

    def test_verified_tutor_cannot_create_schools_listing(self):
        user = make_user(role=UserRole.TUTOR, verified=True)
        client = auth_client(user)
        resp = client.post(
            LISTINGS_URL,
            _listing_payload(category=ListingCategory.SCHOOLS),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_verified_masterclass_creates_masterclasses_listing(self):
        user = make_user(role=UserRole.MASTERCLASS, verified=True)
        client = auth_client(user)
        payload = _listing_payload(
            title="Pottery Workshop",
            category=ListingCategory.MASTERCLASSES,
        )
        resp = client.post(LISTINGS_URL, payload, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["status"], ListingStatus.PENDING)
        self.assertEqual(resp.data["category"], ListingCategory.MASTERCLASSES)

    def test_masterclass_cannot_create_tutoring_listing(self):
        user = make_user(role=UserRole.MASTERCLASS, verified=True)
        client = auth_client(user)
        resp = client.post(
            LISTINGS_URL,
            _listing_payload(category=ListingCategory.TUTORING),
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("category", resp.data)

    def test_unverified_tutor_creates_with_draft_status(self):
        user = make_user(role=UserRole.TUTOR, verified=False)
        client = auth_client(user)
        resp = client.post(LISTINGS_URL, _listing_payload(), format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["status"], ListingStatus.DRAFT)

    def test_status_in_body_is_ignored(self):
        """Any status value in the request body must be overridden by the server."""
        user = make_user(role=UserRole.TUTOR, verified=True)
        client = auth_client(user)
        payload = _listing_payload()
        payload["status"] = ListingStatus.ACTIVE
        resp = client.post(LISTINGS_URL, payload, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["status"], ListingStatus.PENDING)

    def test_owner_in_body_is_ignored(self):
        """Any owner value in the body must be discarded; owner = caller."""
        user1 = make_user(role=UserRole.TUTOR, verified=True)
        user2 = make_user(role=UserRole.TUTOR, verified=True)
        client = auth_client(user1)
        payload = _listing_payload()
        payload["owner"] = user2.id
        resp = client.post(LISTINGS_URL, payload, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["owner_id"], str(user1.id))

    def test_family_cannot_create_listing(self):
        user = make_user(role=UserRole.FAMILY, verified=True)
        client = auth_client(user)
        resp = client.post(LISTINGS_URL, _listing_payload(), format="json")
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_cannot_create_listing(self):
        client = APIClient()
        resp = client.post(LISTINGS_URL, _listing_payload(), format="json")
        self.assertEqual(resp.status_code, 401)


class ProviderListingListTests(APITestCase):
    def test_provider_sees_only_own_listings(self):
        user1 = make_user(role=UserRole.TUTOR, verified=True)
        user2 = make_user(role=UserRole.TUTOR, verified=True)
        Listing.objects.create(
            title="Listing A",
            category=ListingCategory.TUTORING,
            owner=user1,
            status=ListingStatus.PENDING,
        )
        Listing.objects.create(
            title="Listing B",
            category=ListingCategory.TUTORING,
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
    def test_tutor_can_get_own_listing(self):
        user = make_user(role=UserRole.TUTOR, verified=True)
        listing = Listing.objects.create(
            title="Own Listing",
            category=ListingCategory.TUTORING,
            owner=user,
            status=ListingStatus.PENDING,
        )
        client = auth_client(user)
        resp = client.get(f"{LISTINGS_URL}{listing.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["title"], "Own Listing")

    def test_tutor_get_other_listing_returns_404(self):
        user1 = make_user(role=UserRole.TUTOR, verified=True)
        user2 = make_user(role=UserRole.TUTOR, verified=True)
        listing = Listing.objects.create(
            title="Other Listing",
            category=ListingCategory.TUTORING,
            owner=user2,
            status=ListingStatus.PENDING,
        )
        client = auth_client(user1)
        resp = client.get(f"{LISTINGS_URL}{listing.id}/")
        self.assertEqual(resp.status_code, 404)


class ProviderListingUpdateTests(APITestCase):
    def test_tutor_patch_own_listing(self):
        user = make_user(role=UserRole.TUTOR, verified=True)
        listing = Listing.objects.create(
            title="Old Title",
            category=ListingCategory.TUTORING,
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

    def test_unverified_tutor_patch_stays_draft(self):
        user = make_user(role=UserRole.TUTOR, verified=False)
        listing = Listing.objects.create(
            title="Draft",
            category=ListingCategory.TUTORING,
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
        user = make_user(role=UserRole.TUTOR, verified=True)
        listing = Listing.objects.create(
            title="Tutor Listing",
            category=ListingCategory.TUTORING,
            owner=user,
            status=ListingStatus.PENDING,
        )
        client = auth_client(user)
        resp = client.patch(
            f"{LISTINGS_URL}{listing.id}/",
            {"category": ListingCategory.MASTERCLASSES},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("category", resp.data)

    def test_tutor_patch_another_listing_returns_404(self):
        user1 = make_user(role=UserRole.TUTOR, verified=True)
        user2 = make_user(role=UserRole.TUTOR, verified=True)
        listing = Listing.objects.create(
            title="Other",
            category=ListingCategory.TUTORING,
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
    def test_tutor_delete_own_listing(self):
        user = make_user(role=UserRole.TUTOR, verified=True)
        listing = Listing.objects.create(
            title="To Delete",
            category=ListingCategory.TUTORING,
            owner=user,
            status=ListingStatus.PENDING,
        )
        client = auth_client(user)
        resp = client.delete(f"{LISTINGS_URL}{listing.id}/")
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(Listing.objects.filter(id=listing.id).exists())

    def test_tutor_delete_another_listing_returns_404(self):
        user1 = make_user(role=UserRole.TUTOR, verified=True)
        user2 = make_user(role=UserRole.TUTOR, verified=True)
        listing = Listing.objects.create(
            title="Not Mine",
            category=ListingCategory.TUTORING,
            owner=user2,
            status=ListingStatus.PENDING,
        )
        client = auth_client(user1)
        resp = client.delete(f"{LISTINGS_URL}{listing.id}/")
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Listing.objects.filter(id=listing.id).exists())


class ProviderListingPublicVisibilityTests(APITestCase):
    def test_pending_listing_not_visible_in_public_api(self):
        user = make_user(role=UserRole.TUTOR, verified=True)
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
        user = make_user(role=UserRole.TUTOR, verified=True)
        listing = Listing.objects.create(
            title="Approved Listing",
            category=ListingCategory.TUTORING,
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
