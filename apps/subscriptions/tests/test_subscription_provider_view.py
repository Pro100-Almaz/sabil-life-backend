"""
Tests for provider-side subscription endpoints.

Covers:
- Provider sees only their masterclass subscriptions.
- Isolation across providers.
- Provider serializer omits family contact details.
- Filters: ?status=, ?listing_id=
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.subscriptions.models import MasterclassSubscription, SubscriptionStatus
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.FAMILY, **kw):
    return User.objects.create_user(email=email, password="pass1234!", role=role, **kw)


def make_listing(owner):
    return Listing.objects.create(
        title="Provider MC Listing",
        category=ListingCategory.MASTERCLASSES,
        status=ListingStatus.ACTIVE,
        owner=owner,
    )


def make_subscription(family, listing, provider, sub_status=SubscriptionStatus.CONFIRMED):
    return MasterclassSubscription.objects.create(
        family=family,
        listing=listing,
        provider=provider,
        status=sub_status,
    )


class ProviderSubscriptionViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.mc_provider = make_user(
            "mc_prov@test.com", UserRole.MASTERCLASS, full_name="MC Provider"
        )
        cls.other_mc_provider = make_user("other_mc_prov@test.com", UserRole.MASTERCLASS)
        cls.family = make_user(
            "fam_prov_sub@test.com", UserRole.FAMILY, full_name="Sara Test"
        )
        cls.listing = make_listing(cls.mc_provider)
        cls.other_listing = make_listing(cls.other_mc_provider)
        cls.subscription = make_subscription(cls.family, cls.listing, cls.mc_provider)
        cls.other_sub = make_subscription(
            cls.family, cls.other_listing, cls.other_mc_provider
        )

    def _list_url(self):
        return reverse("v1:provider-subscriptions:provider-subscriptions-list")

    def _detail_url(self, sub_id):
        return reverse(
            "v1:provider-subscriptions:provider-subscriptions-detail",
            kwargs={"id": str(sub_id)},
        )

    # ------------------------------------------------------------------
    # Isolation
    # ------------------------------------------------------------------

    def test_provider_sees_own_subscriptions(self):
        self.client.force_authenticate(user=self.mc_provider)
        resp = self.client.get(self._list_url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in resp.data["results"]]
        self.assertIn(str(self.subscription.id), ids)

    def test_provider_does_not_see_other_providers_subscriptions(self):
        self.client.force_authenticate(user=self.mc_provider)
        resp = self.client.get(self._list_url())
        ids = [r["id"] for r in resp.data["results"]]
        self.assertNotIn(str(self.other_sub.id), ids)

    def test_other_provider_cannot_access_detail(self):
        self.client.force_authenticate(user=self.other_mc_provider)
        resp = self.client.get(self._detail_url(self.subscription.id))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------
    # Filters
    # ------------------------------------------------------------------

    def test_status_filter(self):
        self.client.force_authenticate(user=self.mc_provider)
        resp = self.client.get(self._list_url(), {"status": "CONFIRMED"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for r in resp.data["results"]:
            self.assertEqual(r["status"], "CONFIRMED")

    def test_listing_id_filter(self):
        self.client.force_authenticate(user=self.mc_provider)
        resp = self.client.get(self._list_url(), {"listing_id": str(self.listing.id)})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for r in resp.data["results"]:
            self.assertEqual(r["listing_id"], str(self.listing.id))

    # ------------------------------------------------------------------
    # Serializer shape — family contact omitted
    # ------------------------------------------------------------------

    def test_provider_response_includes_family_id_and_full_name(self):
        self.client.force_authenticate(user=self.mc_provider)
        resp = self.client.get(self._detail_url(self.subscription.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        family_block = resp.data["family"]
        self.assertIn("id", family_block)
        self.assertIn("full_name", family_block)

    def test_provider_response_does_not_include_family_phone_or_email(self):
        """Provider serializer omits phone and email in Phase 5."""
        self.client.force_authenticate(user=self.mc_provider)
        resp = self.client.get(self._detail_url(self.subscription.id))
        family_block = resp.data["family"]
        self.assertNotIn("phone", family_block)
        self.assertNotIn("email", family_block)

    def test_provider_response_includes_listing_title(self):
        self.client.force_authenticate(user=self.mc_provider)
        resp = self.client.get(self._detail_url(self.subscription.id))
        self.assertIn("listing_title", resp.data)

    def test_family_cannot_access_provider_subscription_endpoints(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.get(self._list_url())
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
