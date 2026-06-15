"""
Tests for POST /api/v1/suggestions/ (create suggestion).
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


class SuggestionCreateViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("v1:suggestions:suggestions-list")
        cls.family = make_user("fam_sug_c@test.com", UserRole.FAMILY)
        cls.tutor = make_user("tut_sug_c@test.com", UserRole.TUTOR)
        cls.mc_provider = make_user("mc_sug_c@test.com", UserRole.MASTERCLASS)
        cls.admin_user = make_user("adm_sug_c@test.com", UserRole.ADMIN)

    # ------------------------------------------------------------------
    # Happy path — full body
    # ------------------------------------------------------------------

    def test_family_can_create_suggestion_with_full_body(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.post(
            self.url,
            {
                "category": "MASTERCLASSES",
                "neighborhood": "Lusail",
                "message": "Kids pottery class please.",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["category"], "MASTERCLASSES")
        self.assertEqual(resp.data["neighborhood"], "Lusail")
        self.assertEqual(resp.data["message"], "Kids pottery class please.")
        self.assertEqual(resp.data["status"], "NEW")

    # ------------------------------------------------------------------
    # Happy path — message only (category and neighborhood optional)
    # ------------------------------------------------------------------

    def test_family_can_create_suggestion_with_message_only(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.post(
            self.url,
            {"message": "Just a message, no category or neighborhood."},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            resp.data["message"], "Just a message, no category or neighborhood."
        )

    # ------------------------------------------------------------------
    # admin_notes not in response
    # ------------------------------------------------------------------

    def test_admin_notes_not_in_create_response(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.post(self.url, {"message": "Test suggestion."})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("admin_notes", resp.data)

    # ------------------------------------------------------------------
    # Role restrictions
    # ------------------------------------------------------------------

    def test_tutor_cannot_create_suggestion(self):
        self.client.force_authenticate(user=self.tutor)
        resp = self.client.post(self.url, {"message": "Tutor suggestion."})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_mc_provider_cannot_create_suggestion(self):
        self.client.force_authenticate(user=self.mc_provider)
        resp = self.client.post(self.url, {"message": "MC suggestion."})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_create_suggestion_via_api(self):
        self.client.force_authenticate(user=self.admin_user)
        resp = self.client.post(self.url, {"message": "Admin suggestion."})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_create_suggestion(self):
        resp = self.client.post(self.url, {"message": "Anonymous suggestion."})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # Validation — message required
    # ------------------------------------------------------------------

    def test_missing_message_returns_400(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.post(self.url, {"category": "MASTERCLASSES"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Created row has correct owner
    # ------------------------------------------------------------------

    def test_suggestion_created_with_correct_family(self):
        self.client.force_authenticate(user=self.family)
        resp = self.client.post(self.url, {"message": "Family ownership test."})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        suggestion = ServiceSuggestion.objects.get(id=resp.data["id"])
        self.assertEqual(suggestion.family_id, self.family.id)
