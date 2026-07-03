from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from apps.notifications.models import Device, Notification


@admin.register(Device)
class DeviceAdmin(ModelAdmin):
    list_display = ("user_email", "platform", "is_active", "last_seen_at")
    list_filter = ("platform", "is_active")
    search_fields = ("user__email", "fcm_token")
    readonly_fields = ("user", "fcm_token", "platform", "created_at", "last_seen_at")

    @admin.display(description=_("Email"), ordering="user__email")
    def user_email(self, obj: Device) -> str:
        return obj.user.email


@admin.register(Notification)
class NotificationAdmin(ModelAdmin):
    list_display = ("user_email", "type", "title", "is_read", "created_at")
    list_filter = ("type", "is_read")
    search_fields = ("user__email", "title", "body")
    readonly_fields = (
        "user",
        "type",
        "title",
        "body",
        "data",
        "is_read",
        "read_at",
        "created_at",
    )

    @admin.display(description=_("Email"), ordering="user__email")
    def user_email(self, obj: Notification) -> str:
        return obj.user.email
