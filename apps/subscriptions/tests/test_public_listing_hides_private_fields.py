"""
Regression test: public listing endpoints MUST NOT leak private fields.

Verifies that session_schedule, exact_address, and materials_required are NOT
present in GET /api/v1/listings/ and GET /api/v1/listings/{id}/ responses,
even for a MASTERCLASSES listing that has those fields populated.
"""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.catalog.models import Listing, ListingCategory, ListingStatus

PRIVATE_FIELDS = ("session_schedule", "exact_address", "materials_required")


class PublicListingHidesPrivateFieldsTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.listing = Listing.objects.create(
            title="Pottery Masterclass",
            category=ListingCategory.MASTERCLASSES,
            status=ListingStatus.ACTIVE,
            session_schedule="Saturday mornings 9-11am",
            exact_address="Building 5, Lusail",
            materials_required=["Clay", "Pottery wheel"],
        )

    def _list_url(self):
        return reverse("v1:catalog:listings-list")

    def _detail_url(self):
        return reverse(
            "v1:catalog:listings-detail",
            kwargs={"id": str(self.listing.id)},
        )

    def test_list_does_not_leak_session_schedule(self):
        resp = self.client.get(self._list_url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for result in resp.data["results"]:
            self.assertNotIn("session_schedule", result)

    def test_list_does_not_leak_exact_address(self):
        resp = self.client.get(self._list_url())
        for result in resp.data["results"]:
            self.assertNotIn("exact_address", result)

    def test_list_does_not_leak_materials_required(self):
        resp = self.client.get(self._list_url())
        for result in resp.data["results"]:
            self.assertNotIn("materials_required", result)

    def test_detail_does_not_leak_session_schedule(self):
        resp = self.client.get(self._detail_url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertNotIn("session_schedule", resp.data)

    def test_detail_does_not_leak_exact_address(self):
        resp = self.client.get(self._detail_url())
        self.assertNotIn("exact_address", resp.data)

    def test_detail_does_not_leak_materials_required(self):
        resp = self.client.get(self._detail_url())
        self.assertNotIn("materials_required", resp.data)
