"""
Notification views.

Device endpoints (any authenticated user):
  POST /api/v1/notifications/devices/             — register/refresh FCM token
  POST /api/v1/notifications/devices/unregister/  — deactivate token (on logout)

Feed endpoints (any authenticated user):
  GET  /api/v1/notifications/                 — own notifications, recent first
  GET  /api/v1/notifications/{id}/            — detail of own notification
  GET  /api/v1/notifications/unread-count/    — {"unread": <int>} for a badge
  POST /api/v1/notifications/{id}/read/       — mark one read
  POST /api/v1/notifications/read-all/        — mark all read

Every queryset is scoped to request.user — a user can only ever see or mutate
their own devices and notifications.
"""

import logging

from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.notifications.models import Device, Notification
from apps.notifications.serializers import (
    DeviceRegisterSerializer,
    NotificationSerializer,
)

logger = logging.getLogger(__name__)


class DeviceViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Register and unregister this device's FCM token."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DeviceRegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Upsert on the unique token: re-bind to this user and reactivate.
        device, _ = Device.objects.update_or_create(
            fcm_token=serializer.validated_data["fcm_token"],
            defaults={
                "user": request.user,
                "platform": serializer.validated_data["platform"],
                "is_active": True,
            },
        )
        return Response(
            DeviceRegisterSerializer(device).data, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"])
    def unregister(self, request):
        """Deactivate a token — called by the app on logout."""
        Device.objects.filter(
            user=request.user, fcm_token=request.data.get("fcm_token")
        ).update(is_active=False)
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """The caller's in-app notification feed."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = NotificationSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"unread": count})

    @action(detail=True, methods=["post"])
    def read(self, request, id=None):
        updated = self.get_queryset().filter(id=id, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({"updated": updated})

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        updated = self.get_queryset().filter(is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return Response({"updated": updated})
