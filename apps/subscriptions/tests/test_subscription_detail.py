"""
Tests for GET /api/v1/subscriptions/{id}/ — private fields visible to subscribed family.
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


class SubscriptionDetailViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.family = make_user("fam_det@test.com", UserRole.FAMILY)
        cls.other_family = make_user("other_fam_det@test.com", UserRole.FAMILY)
        cls.mc_provider = make_user("mc_det@test.com", UserRole.MASTERCLASS)
        cls.listing = Listing.objects.create(
            title="Detail MC Listing",
            category=ListingCategory.MASTERCLASSES,
            status=ListingStatus.ACTIVE,
            owner=cls.mc_provider,
            session_schedule="Sundays 10am",
            exact_address="Pearl Qatar, Building 3",
            materials_required=["Watercolours", "Canvas"],
        )
        cls.subscription = MasterclassSubscription.objects.create(
            family=cls.family,
            listing=cls.listing,
            provider=cls.mc_provider,
            status=SubscriptionStatus.CONFIRMED,
        )

    def _url(self, sub_id):
        return reverse(
            "v1:subscriptions:subscriptions-detail",
            kwargs={"id": str(sub_id)},
        )

    def test_family_can_retrieve_own_subscription(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.get(self._url(self.subscription.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_private_fields_visible_in_detail(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.get(self._url(self.subscription.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        details = resp.data["listing_private_details"]
        self.assertEqual(details["session_schedule"], "Sundays 10am")
        self.assertEqual(details["exact_address"], "Pearl Qatar, Building 3")
        self.assertEqual(details["materials_required"], ["Watercolours", "Canvas"])

    def test_other_family_gets_404(self):
        self.client.force_authenticate(user=self.other_family)
        resp = self.client.get(self._url(self.subscription.id))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_gets_401(self):
        resp = self.client.get(self._url(self.subscription.id))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_response_contains_expected_fields(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.get(self._url(self.subscription.id))
        for field in (
            "id",
            "listing_id",
            "provider_id",
            "status",
            "cancelled_at",
            "created_at",
            "updated_at",
            "listing_private_details",
        ):
            self.assertIn(field, resp.data)
