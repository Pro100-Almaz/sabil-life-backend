from unittest.mock import patch

from rest_framework.test import APITestCase

from apps.catalog.models import Listing, ListingCategory, ListingStatus, ListingTag
from apps.providers.models import ListingOwnershipRequest, StatusChoices
from apps.providers.tests.test_provider_listings_view import auth_client, make_user
from apps.users.enums import UserRole

REQUESTS_URL = "/api/v1/provider/ownership-requests/"
ADMIN_URL = "/api/v1/provider/ownership-requests/admin/"
LISTINGS_URL = "/api/v1/provider/listings/"


def make_listing(**kwargs) -> Listing:
    defaults = {
        "title": "Doha Academy",
        "category": ListingCategory.SCHOOLS,
        "status": ListingStatus.ACTIVE,
    }
    return Listing.objects.create(**{**defaults, **kwargs})


class OwnershipRequestTests(APITestCase):
    def setUp(self):
        self.provider = make_user([UserRole.MASTERCLASS])
        self.admin = make_user([UserRole.ADMIN])
        self.listing = make_listing()
        self.client = auth_client(self.provider)

    def _request(self, listing=None, client=None):
        return (client or self.client).post(
            REQUESTS_URL,
            {"listing_id": str((listing or self.listing).id), "message": "Mine"},
            format="json",
        )

    def test_provider_can_request_ownership(self):
        res = self._request()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], StatusChoices.PENDING)
        self.assertEqual(ListingOwnershipRequest.objects.count(), 1)

    def test_duplicate_pending_request_rejected(self):
        self._request()
        self.assertEqual(self._request().status_code, 400)

    def test_cannot_request_own_or_inactive_listing(self):
        own = make_listing(owner=self.provider)
        draft = make_listing(status=ListingStatus.DRAFT)
        self.assertEqual(self._request(own).status_code, 400)
        self.assertEqual(self._request(draft).status_code, 400)

    def test_non_provider_forbidden(self):
        family = make_user([UserRole.FAMILY])
        self.assertEqual(self._request(client=auth_client(family)).status_code, 403)

    def test_cancel_pending_request(self):
        req_id = self._request().data["id"]
        res = self.client.delete(f"{REQUESTS_URL}{req_id}/")
        self.assertEqual(res.status_code, 204)
        self.assertEqual(
            ListingOwnershipRequest.objects.get(id=req_id).status,
            StatusChoices.CANCELLED,
        )

    def test_list_only_own_requests(self):
        self._request()
        other = make_user([UserRole.MASTERCLASS])
        self._request(client=auth_client(other))
        res = self.client.get(REQUESTS_URL)
        self.assertEqual(len(res.data), 1)

    @patch("apps.notifications.tasks.notify_ownership_result.delay")
    def test_admin_approval_transfers_ownership(self, _delay):
        req_id = self._request().data["id"]
        rival = make_user([UserRole.MASTERCLASS])
        self._request(client=auth_client(rival))
        admin = auth_client(self.admin)

        with self.captureOnCommitCallbacks(execute=True):
            res = admin.patch(
                f"{ADMIN_URL}{req_id}/", {"status": "APPROVED"}, format="json"
            )
        self.assertEqual(res.status_code, 200)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.owner, self.provider)
        rival_req = ListingOwnershipRequest.objects.get(user=rival)
        self.assertEqual(rival_req.status, StatusChoices.REJECTED)

    @patch("apps.notifications.tasks.notify_ownership_result.delay")
    def test_rejection_requires_comment(self, _delay):
        req_id = self._request().data["id"]
        admin = auth_client(self.admin)
        res = admin.patch(f"{ADMIN_URL}{req_id}/", {"status": "REJECTED"}, format="json")
        self.assertEqual(res.status_code, 400)
        res = admin.patch(
            f"{ADMIN_URL}{req_id}/",
            {"status": "REJECTED", "comment": "No proof"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.listing.refresh_from_db()
        self.assertIsNone(self.listing.owner)

    def test_provider_cannot_review(self):
        req_id = self._request().data["id"]
        res = self.client.patch(
            f"{ADMIN_URL}{req_id}/", {"status": "APPROVED"}, format="json"
        )
        self.assertEqual(res.status_code, 403)


class OwnedListingEditTests(APITestCase):
    def setUp(self):
        self.provider = make_user([UserRole.MASTERCLASS])
        self.listing = make_listing(owner=self.provider)
        self.client = auth_client(self.provider)
        self.tag = ListingTag.objects.create(name="IB", category=ListingCategory.SCHOOLS)
        self.url = f"{LISTINGS_URL}{self.listing.id}/"

    def test_owner_edits_details_and_tags_keeping_category(self):
        res = self.client.patch(
            self.url,
            {"description": "New", "tags": ["IB"], "category": "SCHOOLS"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["tag_names"], ["IB"])
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.description, "New")

    def test_unknown_tag_rejected(self):
        res = self.client.patch(self.url, {"tags": ["Nope"]}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_cannot_move_to_disallowed_category(self):
        res = self.client.patch(self.url, {"category": "NURSERIES"}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_non_owner_gets_404(self):
        other = auth_client(make_user([UserRole.MASTERCLASS]))
        res = other.patch(self.url, {"description": "x"}, format="json")
        self.assertEqual(res.status_code, 404)
