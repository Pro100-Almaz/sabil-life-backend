"""Tests for the public tutor directory visibility rules."""

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.providers.models import TutorDetail, TutorStatus
from apps.users.enums import UserRole
from apps.users.models import CustomUser


def make_tutor(
    email: str,
    *,
    tutor_status: str = TutorStatus.ACTIVE,
    deleted: bool = False,
    user_is_active: bool = True,
) -> TutorDetail:
    user = CustomUser.objects.create_user(
        email=email,
        password="TestPass123!",
        full_name=email.split("@")[0],
        role=UserRole.TUTOR,
        is_active=user_is_active,
    )
    return TutorDetail.objects.create(
        user=user,
        status=tutor_status,
        deleted_at=timezone.now() if deleted else None,
    )


class TutorListViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("v1:catalog:tutors-list")

    def test_only_publicly_available_tutors_are_listed(self):
        active = make_tutor("active@example.com")
        make_tutor("paused@example.com", tutor_status=TutorStatus.PAUSED)
        make_tutor("deleted@example.com", deleted=True)
        make_tutor("disabled@example.com", user_is_active=False)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in response.data["results"]]
        self.assertEqual(ids, [active.id])

    def test_authenticated_tutor_does_not_see_own_profile(self):
        current_tutor = make_tutor("current@example.com")
        other_tutor = make_tutor("other@example.com")
        self.client.force_authenticate(current_tutor.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in response.data["results"]]
        self.assertNotIn(current_tutor.id, ids)
        self.assertIn(other_tutor.id, ids)
