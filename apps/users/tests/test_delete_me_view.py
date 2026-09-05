from knox.models import AuthToken
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from apps.users.models import CustomUser


class DeleteMeViewTests(APITestCase):
    def setUp(self):
        self.password = "StrongPassword!123"
        self.user = CustomUser.objects.create_user(
            email="delete-me@example.com",
            password=self.password,
        )
        _, token = AuthToken.objects.create(self.user)

        self.url = reverse("v1:users:delete-me")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_password_is_required(self):
        response = self.client.delete(self.url, data={}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_incorrect_password_is_rejected(self):
        response = self.client.delete(
            self.url,
            data={"password": "WrongPassword!123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_authentication_is_required(self):
        self.client.credentials()

        response = self.client.delete(
            self.url,
            data={"password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_deletes_and_anonymizes_account(self):
        AuthToken.objects.create(self.user)
        original_email = self.user.email
        self.user.full_name = "Delete Me"
        self.user.phone = "+97455555555"
        self.user.home_lat = 25.2854
        self.user.home_lng = 51.5310
        self.user.save()

        response = self.client.delete(
            self.url,
            data={"password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.content, b"")

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.user.is_verified)
        self.assertIsNotNone(self.user.deleted_at)
        self.assertNotEqual(self.user.email, original_email)
        self.assertTrue(self.user.email.endswith("@deleted.invalid"))
        self.assertEqual(self.user.full_name, "")
        self.assertEqual(self.user.phone, "")
        self.assertIsNone(self.user.home_lat)
        self.assertIsNone(self.user.home_lng)
        self.assertFalse(self.user.has_usable_password())
        self.assertFalse(AuthToken.objects.filter(user=self.user).exists())

    def test_deleted_email_can_be_registered_again(self):
        response = self.client.delete(
            self.url,
            data={"password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        replacement = CustomUser.objects.create_user(
            email="delete-me@example.com",
            password="AnotherStrongPassword!123",
        )
        self.assertEqual(replacement.email, "delete-me@example.com")
