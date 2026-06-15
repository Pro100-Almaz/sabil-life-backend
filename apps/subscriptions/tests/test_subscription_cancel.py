"""
Tests for DELETE /api/v1/subscriptions/{id}/ — soft cancel + re-subscribe.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.subscriptions.models import MasterclassSubscription, SubscriptionStatus
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.FAMILY):
    return User.objects.create_user(email=email, password="pass1234!", role=role)


class SubscriptionCancelViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mc_provider = make_user("mc_cancel@test.com", UserRole.MASTERCLASS)
        cls.listing = Listing.objects.create(
            title="Cancel MC Listing",
            category=ListingCategory.MASTERCLASSES,
            status=ListingStatus.ACTIVE,
            owner=cls.mc_provider,
        )

    def _detail_url(self, sub_id):
        return reverse(
            "v1:subscriptions:subscriptions-detail",
            kwargs={"id": str(sub_id)},
        )

    def _create_url(self):
        return reverse("v1:subscriptions:subscriptions-list")

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------

    def test_delete_soft_cancels_subscription(self):
        family = make_user("fam_cancel1@test.com", UserRole.FAMILY)
        sub = MasterclassSubscription.objects.create(
            family=family,
            listing=self.listing,
            provider=self.mc_provider,
            status=SubscriptionStatus.CONFIRMED,
        )
        self.client.force_authenticate(user=family)
        resp = self.client.delete(self._detail_url(sub.id))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        sub.refresh_from_db()
        self.assertEqual(sub.status, SubscriptionStatus.CANCELLED)
        self.assertIsNotNone(sub.cancelled_at)

    def test_delete_returns_204(self):
        family = make_user("fam_cancel2@test.com", UserRole.FAMILY)
        sub = MasterclassSubscription.objects.create(
            family=family,
            listing=self.listing,
            provider=self.mc_provider,
            status=SubscriptionStatus.CONFIRMED,
        )
        self.client.force_authenticate(user=family)
        resp = self.client.delete(self._detail_url(sub.id))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_does_not_hard_delete_row(self):
        family = make_user("fam_cancel3@test.com", UserRole.FAMILY)
        sub = MasterclassSubscription.objects.create(
            family=family,
            listing=self.listing,
            provider=self.mc_provider,
            status=SubscriptionStatus.CONFIRMED,
        )
        sub_id = sub.id
        self.client.force_authenticate(user=family)
        self.client.delete(self._detail_url(sub_id))
        self.assertTrue(MasterclassSubscription.objects.filter(id=sub_id).exists())

    def test_other_family_cannot_cancel(self):
        family = make_user("fam_cancel4@test.com", UserRole.FAMILY)
        other_family = make_user("other_cancel@test.com", UserRole.FAMILY)
        sub = MasterclassSubscription.objects.create(
            family=family,
            listing=self.listing,
            provider=self.mc_provider,
            status=SubscriptionStatus.CONFIRMED,
        )
        self.client.force_authenticate(user=other_family)
        resp = self.client.delete(self._detail_url(sub.id))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------
    # Re-subscribe after cancel
    # ------------------------------------------------------------------

    def test_family_can_resubscribe_after_cancellation(self):
        family = make_user("fam_resub@test.com", UserRole.FAMILY)
        sub = MasterclassSubscription.objects.create(
            family=family,
            listing=self.listing,
            provider=self.mc_provider,
            status=SubscriptionStatus.CONFIRMED,
        )
        self.client.force_authenticate(user=family)
        # Cancel
        self.client.delete(self._detail_url(sub.id))
        # Re-subscribe
        resp = self.client.post(
            self._create_url(),
            {"listing_id": str(self.listing.id)},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], SubscriptionStatus.CONFIRMED)
