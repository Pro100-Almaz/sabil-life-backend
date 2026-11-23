import uuid
from datetime import timedelta
from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.catalog.models import Event, Listing, ListingCategory, ListingStatus
from apps.notifications.models import Notification, NotificationType
from apps.notifications.tasks import notify_provider_event
from apps.providers.models import ProviderFollow
from apps.providers.tests.test_provider_listings_view import auth_client, make_user
from apps.users.enums import UserRole

FOLLOW_URL = "/api/v1/provider-subscriptions/"
SUBSCRIBERS_URL = "/api/v1/provider/subscribers/"


class ProviderFollowTests(APITestCase):
    def setUp(self):
        self.provider = make_user()
        self.other_provider = make_user([UserRole.TUTOR])
        self.family = make_user([UserRole.FAMILY])
        self.other_family = make_user([UserRole.FAMILY])
        self.client = auth_client(self.family)

    def subscribe(self, provider=None, client=None):
        return (client or self.client).post(
            FOLLOW_URL,
            {"provider_id": str((provider or self.provider).uuid)},
            format="json",
        )

    def test_subscribe_duplicate_unsubscribe_and_resubscribe(self):
        response = self.subscribe()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["provider_id"], str(self.provider.uuid))
        self.assertEqual(self.subscribe().status_code, 200)
        self.assertEqual(ProviderFollow.objects.count(), 1)
        url = f"{FOLLOW_URL}{self.provider.uuid}/"
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertFalse(ProviderFollow.objects.exists())
        self.assertEqual(self.subscribe().status_code, 201)

    def test_database_rejects_duplicates_and_self_subscription(self):
        self.subscribe()
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProviderFollow.objects.create(client=self.family, provider=self.provider)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProviderFollow.objects.create(client=self.provider, provider=self.provider)

    def test_list_only_own_providers_without_subscriber_details(self):
        self.subscribe()
        self.subscribe(self.other_provider)
        self.subscribe(client=auth_client(self.other_family))
        response = self.client.get(FOLLOW_URL, {"client_id": str(self.other_family.uuid)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            {row["provider_id"] for row in response.data["results"]},
            {str(self.provider.uuid), str(self.other_provider.uuid)},
        )
        for row in response.data["results"]:
            self.assertEqual(set(row), {"provider_id", "display_name"})

    def test_client_cannot_delete_another_clients_subscription(self):
        self.subscribe()
        response = auth_client(self.other_family).delete(
            f"{FOLLOW_URL}{self.provider.uuid}/"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(ProviderFollow.objects.count(), 1)

    def test_client_identity_is_taken_from_authentication(self):
        response = self.client.post(
            FOLLOW_URL,
            {
                "provider_id": str(self.provider.uuid),
                "client_id": str(self.other_family.uuid),
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(ProviderFollow.objects.get().client, self.family)

    def test_invalid_targets_and_self_subscription_rejected(self):
        for provider_id in [uuid.uuid4(), self.family.uuid]:
            response = self.client.post(FOLLOW_URL, {"provider_id": str(provider_id)})
            self.assertEqual(response.status_code, 404)
        for payload in [{}, {"provider_id": "bad-uuid"}]:
            self.assertEqual(self.client.post(FOLLOW_URL, payload).status_code, 400)
        self.assertEqual(
            self.subscribe(client=auth_client(self.provider)).status_code, 400
        )
        self.assertFalse(ProviderFollow.objects.exists())

    def test_inactive_and_deleted_providers_rejected(self):
        self.provider.is_active = False
        self.provider.save()
        self.assertEqual(self.subscribe().status_code, 404)
        self.provider.is_active = True
        self.provider.deleted_at = timezone.now()
        self.provider.save()
        self.assertEqual(self.subscribe().status_code, 404)

    def test_owner_can_view_subscriber_list_detail_and_count(self):
        self.subscribe()
        self.subscribe(client=auth_client(self.other_family))
        client = auth_client(self.provider)
        response = client.get(SUBSCRIBERS_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            {row["client_id"] for row in response.data["results"]},
            {str(self.family.uuid), str(self.other_family.uuid)},
        )
        follow_id = response.data["results"][0]["id"]
        detail = client.get(f"{SUBSCRIBERS_URL}{follow_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertIn("created_at", detail.data)
        self.assertEqual(client.get(f"{SUBSCRIBERS_URL}count/").data, {"count": 2})
        self.client.delete(f"{FOLLOW_URL}{self.provider.uuid}/")
        self.assertEqual(client.get(f"{SUBSCRIBERS_URL}count/").data, {"count": 1})

    def test_other_providers_and_managers_cannot_access_owner_data(self):
        self.subscribe()
        follow = ProviderFollow.objects.get()
        for user in [self.other_provider, make_user([UserRole.MANAGER])]:
            client = auth_client(user)
            query = {"provider_id": str(self.provider.uuid)}
            response = client.get(SUBSCRIBERS_URL, query)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["results"], [])
            self.assertEqual(
                client.get(f"{SUBSCRIBERS_URL}count/", query).data, {"count": 0}
            )
            self.assertEqual(
                client.get(f"{SUBSCRIBERS_URL}{follow.pk}/").status_code, 404
            )

    def test_subscribers_are_read_only_and_unavailable_to_clients(self):
        self.subscribe()
        follow = ProviderFollow.objects.get()
        for url in [
            SUBSCRIBERS_URL,
            f"{SUBSCRIBERS_URL}{follow.pk}/",
            f"{SUBSCRIBERS_URL}count/",
        ]:
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(APIClient().get(url).status_code, 401)
        owner = auth_client(self.provider)
        self.assertEqual(owner.post(SUBSCRIBERS_URL, {}).status_code, 405)
        self.assertEqual(owner.delete(f"{SUBSCRIBERS_URL}{follow.pk}/").status_code, 405)

    def test_anonymous_cannot_manage_follows(self):
        client = APIClient()
        self.assertEqual(client.get(FOLLOW_URL).status_code, 401)
        self.assertEqual(self.subscribe(client=client).status_code, 401)
        self.assertEqual(
            client.delete(f"{FOLLOW_URL}{self.provider.uuid}/").status_code, 401
        )


class ProviderEventNotificationTests(APITestCase):
    def setUp(self):
        self.provider = make_user()
        self.family = make_user([UserRole.FAMILY])
        self.other_family = make_user([UserRole.FAMILY])
        self.follow = ProviderFollow.objects.create(
            client=self.family, provider=self.provider
        )
        self.listing = Listing.objects.create(
            owner=self.provider,
            title="School",
            category=ListingCategory.SCHOOLS,
            status=ListingStatus.ACTIVE,
        )

    def publish(self):
        return Event.objects.create(
            listing=self.listing,
            title="Open day",
            starts_at=timezone.now() + timedelta(days=1),
        )

    @patch("apps.catalog.signals.notify_provider_event.delay")
    def test_api_publication_queues_after_commit_and_edits_do_not(self, delay):
        url = f"/api/v1/provider/listings/{self.listing.pk}/events/"
        client = auth_client(self.provider)
        with self.captureOnCommitCallbacks(execute=True):
            response = client.post(
                url,
                {
                    "title": "Open day",
                    "starts_at": (timezone.now() + timedelta(days=1)).isoformat(),
                },
            )
            self.assertEqual(response.status_code, 201, response.data)
            delay.assert_not_called()
        delay.assert_called_once_with(response.data["id"], self.provider.pk)
        delay.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            client.patch(f"{url}{response.data['id']}/", {"title": "Updated"})
        delay.assert_not_called()

    @patch("apps.catalog.signals.notify_provider_event.delay")
    def test_event_on_non_active_listing_does_not_notify(self, delay):
        self.listing.status = ListingStatus.PENDING
        self.listing.save()
        with self.captureOnCommitCallbacks(execute=True):
            self.publish()
        delay.assert_not_called()

    @patch("apps.catalog.signals.notify_provider_event.delay")
    def test_rollback_does_not_queue_notification(self, delay):
        with self.captureOnCommitCallbacks(execute=True):
            try:
                with transaction.atomic():
                    self.publish()
                    raise ValueError("rollback")
            except ValueError:
                pass
        delay.assert_not_called()

    @patch("apps.notifications.tasks.send_push_to_user")
    def test_follower_receives_one_notification_even_on_task_replay(self, push):
        event = self.publish()
        notify_provider_event.run(str(event.pk), self.provider.pk)
        notify_provider_event.run(str(event.pk), self.provider.pk)
        note = Notification.objects.get()
        self.assertEqual(note.user, self.family)
        self.assertEqual(note.type, NotificationType.PROVIDER_EVENT)
        self.assertEqual(
            note.data,
            {
                "event_id": str(event.pk),
                "listing_id": str(self.listing.pk),
                "provider_id": str(self.provider.uuid),
            },
        )
        push.assert_called_once()
        # The existing inbox exposes the alert only to its recipient.
        response = auth_client(self.family).get("/api/v1/notifications/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            auth_client(self.other_family).get("/api/v1/notifications/").data["count"], 0
        )

    @patch("apps.notifications.tasks.send_push_to_user")
    def test_unsubscribe_and_following_after_publication_do_not_notify(self, push):
        event = self.publish()
        self.follow.delete()
        ProviderFollow.objects.create(client=self.other_family, provider=self.provider)
        notify_provider_event.run(str(event.pk), self.provider.pk)
        self.assertFalse(Notification.objects.exists())
        push.assert_not_called()

    @patch("apps.notifications.tasks.send_push_to_user")
    def test_ownership_transfer_keeps_original_publisher(self, push):
        event = self.publish()
        new_owner = make_user()
        ProviderFollow.objects.create(client=self.other_family, provider=new_owner)
        self.listing.owner = new_owner
        self.listing.save()
        notify_provider_event.run(str(event.pk), self.provider.pk)
        self.assertEqual(Notification.objects.get().user, self.family)
        self.assertEqual(
            Notification.objects.get().data["provider_id"], str(self.provider.uuid)
        )

    @patch(
        "apps.notifications.tasks.send_push_to_user", side_effect=RuntimeError("FCM down")
    )
    def test_push_failure_preserves_all_inbox_notifications(self, push):
        ProviderFollow.objects.create(client=self.other_family, provider=self.provider)
        event = self.publish()
        notify_provider_event.run(str(event.pk), self.provider.pk)
        self.assertEqual(Notification.objects.count(), 2)
        self.assertEqual(push.call_count, 2)

    @patch("apps.notifications.tasks.send_push_to_user")
    def test_deleted_event_and_inactive_clients_are_skipped(self, push):
        event = self.publish()
        event_id = str(event.pk)
        self.family.is_active = False
        self.family.save()
        notify_provider_event.run(event_id, self.provider.pk)
        event.delete()
        notify_provider_event.run(event_id, self.provider.pk)
        self.assertFalse(Notification.objects.exists())
        push.assert_not_called()
