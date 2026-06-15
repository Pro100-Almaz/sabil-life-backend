"""
Tests for POST /api/v1/subscriptions/ (create subscription).
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


def make_listing(
    owner, category=ListingCategory.MASTERCLASSES, lst_status=ListingStatus.ACTIVE
):
    return Listing.objects.create(
        title="MC Listing",
        category=category,
        status=lst_status,
        owner=owner,
        session_schedule="Saturdays 9am",
        exact_address="Building 5, Doha",
        materials_required=["Sketchpad"],
    )


class SubscriptionCreateViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("v1:subscriptions:subscriptions-list")
        cls.family = make_user("fam_sub@test.com", UserRole.FAMILY)
        cls.mc_provider = make_user("mc_sub@test.com", UserRole.MASTERCLASS)
        cls.tutor = make_user("tut_sub@test.com", UserRole.TUTOR)
        cls.admin_user = make_user("adm_sub@test.com", UserRole.ADMIN)
        cls.mc_listing = make_listing(cls.mc_provider, ListingCategory.MASTERCLASSES)
        cls.tutoring_listing = make_listing(cls.tutor, ListingCategory.TUTORING)
        cls.draft_mc_listing = make_listing(
            cls.mc_provider, ListingCategory.MASTERCLASSES, ListingStatus.DRAFT
        )

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    def test_family_can_subscribe_to_masterclass(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.post(self.url, {"listing_id": str(self.mc_listing.id)})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], SubscriptionStatus.CONFIRMED)

    def test_create_response_includes_private_details(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.post(self.url, {"listing_id": str(self.mc_listing.id)})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("listing_private_details", resp.data)
        details = resp.data["listing_private_details"]
        self.assertEqual(details["session_schedule"], "Saturdays 9am")
        self.assertEqual(details["exact_address"], "Building 5, Doha")
        self.assertEqual(details["materials_required"], ["Sketchpad"])

    def test_provider_snapshot_set_correctly(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.post(self.url, {"listing_id": str(self.mc_listing.id)})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["provider_id"], str(self.mc_provider.id))

    # ------------------------------------------------------------------
    # Role restrictions
    # ------------------------------------------------------------------

    def test_tutor_cannot_subscribe(self):
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.post(self.url, {"listing_id": str(self.mc_listing.id)})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_subscribe(self):
        self.client.force_authenticate(user=self.admin_user)
        resp = self.client.post(self.url, {"listing_id": str(self.mc_listing.id)})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_subscribe(self):
        resp = self.client.post(self.url, {"listing_id": str(self.mc_listing.id)})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # Category validation
    # ------------------------------------------------------------------

    def test_subscription_on_tutoring_listing_returns_400(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.post(self.url, {"listing_id": str(self.tutoring_listing.id)})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("inquiries", resp.data["detail"].lower())

    # ------------------------------------------------------------------
    # Status validation
    # ------------------------------------------------------------------

    def test_subscription_on_draft_listing_returns_400(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.post(self.url, {"listing_id": str(self.draft_mc_listing.id)})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Duplicate prevention
    # ------------------------------------------------------------------

    def test_duplicate_confirmed_returns_409(self):
        family2 = make_user("fam_dup@test.com", UserRole.FAMILY)
        self.client.force_authenticate(user=family2)
        resp1 = self.client.post(self.url, {"listing_id": str(self.mc_listing.id)})
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)
        resp2 = self.client.post(self.url, {"listing_id": str(self.mc_listing.id)})
        self.assertEqual(resp2.status_code, status.HTTP_409_CONFLICT)

    def test_fresh_subscription_after_cancellation_works(self):
        """After cancelling, a new subscription is allowed."""
        family3 = make_user("fam_resubscribe@test.com", UserRole.FAMILY)
        # Create a cancelled row so re-subscribe is valid
        MasterclassSubscription.objects.create(
            family=family3,
            listing=self.mc_listing,
            provider=self.mc_provider,
            status=SubscriptionStatus.CANCELLED,
        )
        # Re-subscribe
        self.client.force_authenticate(user=family3)
        resp = self.client.post(self.url, {"listing_id": str(self.mc_listing.id)})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["status"], SubscriptionStatus.CONFIRMED)
