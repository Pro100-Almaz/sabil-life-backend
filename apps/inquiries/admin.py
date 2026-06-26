"""
Inquiry admin.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from apps.inquiries.models import Inquiry


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
    readonly_fields = ("id", "family", "tutor", "created_at", "updated_at")
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

    @admin.display(description=_("Family email"))
    def family_email(self, obj: Inquiry) -> str:
        return obj.family.email if obj.family_id else "—"

    @admin.display(description=_("Tutor"))
    def tutor_name(self, obj: Inquiry) -> str:
        return obj.tutor.user.email if obj.tutor_id else "—"
