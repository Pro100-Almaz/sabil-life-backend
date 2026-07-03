from rest_framework import serializers

from apps.notifications.models import Device, Notification


class DeviceRegisterSerializer(serializers.ModelSerializer):
    """
    Input/output for registering (upserting) an FCM token.
    """

    class Meta:
        model = Device
        fields = ["fcm_token", "platform"]
        extra_kwargs = {"fcm_token": {"validators": []}}


class NotificationSerializer(serializers.ModelSerializer):
    """
    Read-only representation of an in-app notification feed row.
    """

    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "title",
            "body",
            "data",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields
