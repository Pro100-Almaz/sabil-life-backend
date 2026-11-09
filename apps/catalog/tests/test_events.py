from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.catalog.models import Event, Listing, ListingCategory, ListingStatus
from apps.providers.tests.test_provider_listings_view import auth_client, make_user
from apps.users.enums import UserRole


class EventTests(APITestCase):
    def setUp(self):
        self.owner = make_user()
        self.other = make_user()
        self.listing = Listing.objects.create(
            title="School",
            category=ListingCategory.SCHOOLS,
            owner=self.owner,
            status=ListingStatus.ACTIVE,
        )
        self.url = f"/api/v1/provider/listings/{self.listing.id}/events/"
        self.client = auth_client(self.owner)
        self.payload = {
            "title": "Open day",
            "starts_at": (timezone.now() + timedelta(days=1)).isoformat(),
        }

    def create_event(self):
        response = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["id"]

    def test_creation_publishes_and_embeds_in_listing(self):
        event_id = self.create_event()
        event = Event.objects.get(id=event_id)
        self.assertEqual(event.listing, self.listing)
        self.assertIsNotNone(event.published_at)
        for client in [APIClient(), auth_client(self.owner), auth_client(self.other)]:
            self.assertEqual(client.get(f"/api/v1/events/{event_id}/").status_code, 200)
            response = client.get(f"/api/v1/listings/{self.listing.id}/events/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["results"][0]["id"], event_id)
        response = APIClient().get(f"/api/v1/listings/{self.listing.id}/")
        self.assertEqual(response.data["events"][0]["id"], event_id)

    def test_other_provider_cannot_manage_events(self):
        event_id = self.create_event()
        client = auth_client(self.other)
        self.assertEqual(client.post(self.url, self.payload).status_code, 404)
        self.assertEqual(client.get(self.url).status_code, 404)
        detail = f"{self.url}{event_id}/"
        self.assertEqual(client.get(detail).status_code, 404)
        self.assertEqual(client.patch(detail, {"title": "Changed"}).status_code, 404)
        self.assertEqual(client.delete(detail).status_code, 404)

    def test_owner_can_edit_and_delete_but_cannot_reassign(self):
        event_id = self.create_event()
        other_listing = Listing.objects.create(
            title="Other",
            category=ListingCategory.SCHOOLS,
            owner=self.other,
        )
        detail = f"{self.url}{event_id}/"
        response = self.client.patch(
            detail,
            {
                "title": "New title",
                "listing": str(other_listing.id),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        event = Event.objects.get(id=event_id)
        self.assertEqual(event.title, "New title")
        self.assertEqual(event.listing, self.listing)
        self.assertEqual(self.client.delete(detail).status_code, 204)

    def test_nonproviders_and_anonymous_cannot_create(self):
        for client in [APIClient(), auth_client(make_user([UserRole.FAMILY]))]:
            self.assertIn(client.post(self.url, self.payload).status_code, [401, 403])

    def test_ownership_transfer_revokes_previous_owner(self):
        event_id = self.create_event()
        self.listing.owner = self.other
        self.listing.save()
        detail = f"{self.url}{event_id}/"
        self.assertEqual(self.client.patch(detail, {"title": "No"}).status_code, 404)
        self.assertEqual(
            auth_client(self.other).patch(detail, {"title": "Yes"}).status_code, 200
        )

    def test_inactive_parent_does_not_hide_event(self):
        event_id = self.create_event()
        self.listing.status = ListingStatus.DRAFT
        self.listing.save()
        self.assertEqual(APIClient().get(f"/api/v1/events/{event_id}/").status_code, 200)

    def test_invalid_dates_rejected_on_create_and_partial_update(self):
        bad = {**self.payload, "ends_at": timezone.now().isoformat()}
        self.assertEqual(self.client.post(self.url, bad).status_code, 400)
        event_id = self.create_event()
        self.assertEqual(
            self.client.patch(
                f"{self.url}{event_id}/",
                {"ends_at": timezone.now().isoformat()},
            ).status_code,
            400,
        )

    def test_event_cannot_be_accessed_under_another_owned_listing(self):
        event_id = self.create_event()
        listing = Listing.objects.create(
            title="Second",
            category=ListingCategory.SCHOOLS,
            owner=self.owner,
        )
        url = f"/api/v1/provider/listings/{listing.id}/events/{event_id}/"
        self.assertEqual(self.client.patch(url, {"title": "No"}).status_code, 404)
