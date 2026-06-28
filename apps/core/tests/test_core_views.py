from unittest.mock import patch

from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.views import PingRateThrottle


class CoreViewsTests(APITestCase):
    """Test suite for core application views"""

    @classmethod
    def setUpTestData(cls):
        cls.ping_url = reverse("v1:core:ping")
        cls.media_url = reverse("v1:core:media-retrieve")

    def test_ping_view_success(self):
        """Test ping endpoint returns correct response"""
        response = self.client.get(self.ping_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"ping": "pong"})

    def test_ping_view_throttle_config(self):
        """Test ping endpoint throttle configuration"""
        throttle = PingRateThrottle()
        self.assertEqual(throttle.rate, "10/minute")

    def test_ping_view_invalid_methods(self):
        """Test ping endpoint rejects non-GET methods"""
        methods = ["post", "put", "patch", "delete"]
        for method in methods:
            with self.subTest(method=method):
                response = getattr(self.client, method)(self.ping_url)
                self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # @patch("apps.core.views.default_storage.open")
    # @patch("apps.core.views.default_storage.exists", return_value=True)
    # @override_settings(MEDIA_URL = "/media/")
    # def test_media_retrieve_streams_storage_object(self, mock_exists, mock_open):
    #     response = self.client.get(
    #         self.media_url,
    #         {"url": "http://localhost:9001/sabil-life-media/listings/demo/image.png"},
    #     )
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     mock_exists.assert_called_once_with("listings/demo/image.png")
    #     mock_open.assert_called_once_with("listings/demo/image.png", "rb")
    #     self.assertEqual(response["Content-Type"], "image/png")

    def test_media_retrieve_requires_url(self):
        response = self.client.get(self.media_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["detail"], "Query parameter 'url' is required.")

    def test_media_retrieve_rejects_invalid_path(self):
        response = self.client.get(
            self.media_url,
            {"url": "http://localhost:9001/sabil-life-media/../secret.txt"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
