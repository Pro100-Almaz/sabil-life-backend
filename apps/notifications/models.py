from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Platform(models.TextChoices):
    ANDROID = "ANDROID", _("Android")
    IOS = "IOS", _("iOS")


class Device(models.Model):
    """A registered FCM token for one app install belonging to a user.

    One user can have several devices (phone + tablet). A token is deactivated
    (``is_active=False``) rather than deleted when FCM reports it as
    unregistered, so we keep a paper trail without ever re-sending to it.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="devices",
        verbose_name=_("user"),
    )
    fcm_token = models.CharField(_("FCM token"), max_length=255, unique=True)
    platform = models.CharField(
        _("platform"), max_length=10, choices=Platform.choices
    )
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("device")
        verbose_name_plural = _("devices")
        indexes = [models.Index(fields=["user", "is_active"])]

    def __str__(self) -> str:
        return f"Device({self.user.email}, {self.platform})"


class NotificationType(models.TextChoices):
    PROVIDER_APPROVED = "PROVIDER_APPROVED", _("Provider application approved")
    PROVIDER_REJECTED = "PROVIDER_REJECTED", _("Provider application rejected")
    LISTING_APPROVED = "LISTING_APPROVED", _("Listing applicatoin approved") 
    LISTING_REJECTED = "LISTING_REJECTED", _("Listing application rejected")
    INQUIRY_RESPONSE = "INQUIRY_RESPONSE", _("Inquiry responded")
    INQUIRY_REQUEST = "INQUIRY_REQUEST", _("Inquiry requested")


class Notification(models.Model):
    """A persisted in-app notification — the inbox feed.

    Written for every notifiable event regardless of whether a push is sent,
    so the feed is the source of truth and push delivery is a best-effort
    side channel. ``data`` carries the deep-link payload for the mobile app.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("user"),
    )
    type = models.CharField(
        _("type"), max_length=40, choices=NotificationType.choices
    )
    title = models.CharField(_("title"), max_length=255)
    body = models.TextField(_("body"))
    data = models.JSONField(_("data"), default=dict, blank=True)
    is_read = models.BooleanField(_("read"), default=False)
    read_at = models.DateTimeField(_("read at"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read"])]

    def __str__(self) -> str:
        return f"Notification({self.user.email}, {self.type})"
