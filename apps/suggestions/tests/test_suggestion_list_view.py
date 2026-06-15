"""
Tests for GET /api/v1/suggestions/ — family sees own only, admin_notes never in response.
"""

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.suggestions.models import ServiceSuggestion
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.FAMILY, **kw):
    return User.objects.create_user(email=email, password="pass1234!", role=role, **kw)


class SuggestionListViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("v1:suggestions:suggestions-list")
        cls.family = make_user("fam_list@test.com", UserRole.FAMILY)
        cls.other_family = make_user("other_fam_list@test.com", UserRole.FAMILY)
        cls.suggestion = ServiceSuggestion.objects.create(
            family=cls.family,
            message="Pottery class in Lusail.",
            admin_notes="Internal note for admin only.",
        )
        cls.other_suggestion = ServiceSuggestion.objects.create(
            family=cls.other_family,
            message="Other family suggestion.",
            admin_notes="Other admin note.",
        )

    # ------------------------------------------------------------------
    # Isolation — family sees own only
    # ------------------------------------------------------------------

    def test_family_sees_own_suggestions(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in resp.data["results"]]
        self.assertIn(self.suggestion.id, ids)

    def test_family_does_not_see_other_families_suggestions(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.get(self.url)
        ids = [r["id"] for r in resp.data["results"]]
        self.assertNotIn(self.other_suggestion.id, ids)

    def test_other_family_sees_own_only(self):
        self.client.force_authenticate(user=self.other_family)
        resp = self.client.get(self.url)
        ids = [r["id"] for r in resp.data["results"]]
        self.assertIn(self.other_suggestion.id, ids)
        self.assertNotIn(self.suggestion.id, ids)

    # ------------------------------------------------------------------
    # admin_notes never in response
    # ------------------------------------------------------------------

    def test_admin_notes_not_in_list_response(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for result in resp.data["results"]:
            self.assertNotIn("admin_notes", result)

    def test_admin_notes_not_in_detail_response(self):
        self.client.force_authenticate(user=self.family)
        detail_url = reverse(
            "v1:suggestions:suggestions-detail",
            kwargs={"id": self.suggestion.id},
        )
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertNotIn("admin_notes", resp.data)

    # ------------------------------------------------------------------
    # Status visible to family
    # ------------------------------------------------------------------

    def test_status_visible_in_list_response(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.get(self.url)
        for result in resp.data["results"]:
            self.assertIn("status", result)

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    def test_list_is_paginated(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.get(self.url)
        self.assertIn("count", resp.data)
        self.assertIn("results", resp.data)
