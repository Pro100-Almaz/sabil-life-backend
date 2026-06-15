"""
Inquiry admin — Phase 5.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Inquiry


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "family_email",
        "listing_title",
        "contact_revealed",
        "created_at",
    )
    list_filter = ("status", "contact_revealed")
    search_fields = ("family__email", "listing__title", "message")
    readonly_fields = ("id", "family", "listing", "provider", "created_at", "updated_at")
    ordering = ("-created_at",)

    fieldsets = (
        (
            _("Inquiry"),
            {"fields": ("id", "status", "contact_revealed", "message")},
        ),
        (
            _("Parties"),
            {"fields": ("family", "listing", "provider")},
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at")},
        ),
    )

    @admin.display(description=_("Family email"))
    def family_email(self, obj: Inquiry) -> str:
        return obj.family.email if obj.family_id else "—"

    @admin.display(description=_("Listing"))
    def listing_title(self, obj: Inquiry) -> str:
        return obj.listing.title if obj.listing_id else "—"
