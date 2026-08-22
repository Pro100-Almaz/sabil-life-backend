"""
Inquiry admin.
"""

from django.contrib import admin
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from apps.inquiries.models import Inquiry
from apps.notifications.tasks import notify_admin_created_inquiry


@admin.register(Inquiry)
class InquiryAdmin(ModelAdmin):
    list_display = (
        "id",
        "status",
        "family_email",
        "tutor_name",
        "contact_revealed",
        "created_at",
    )
    list_filter = ("status", "contact_revealed")
    search_fields = ("family__email", "tutor__user__email", "message")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)

    fieldsets = (
        (
            _("Inquiry"),
            {"fields": ("id", "status", "contact_revealed", "message")},
        ),
        (
            _("Parties"),
            {"fields": ("family", "tutor")},
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at")},
        ),
    )

    def save_model(self, request, obj, form, change):
        """Notify both parties only for inquiries created in Django Admin."""
        super().save_model(request, obj, form, change)
        if not change:
            transaction.on_commit(
                lambda inquiry_id=obj.id: notify_admin_created_inquiry.delay(inquiry_id)
            )

    @admin.display(description=_("Family email"))
    def family_email(self, obj: Inquiry) -> str:
        return obj.family.email if obj.family_id else "—"

    @admin.display(description=_("Tutor"))
    def tutor_name(self, obj: Inquiry) -> str:
        return obj.tutor.user.email if obj.tutor_id else "—"
