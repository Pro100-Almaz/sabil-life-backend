"""
MasterclassSubscription admin — Phase 5.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import MasterclassSubscription


@admin.register(MasterclassSubscription)
class MasterclassSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "family_email",
        "listing_title",
        "cancelled_at",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("family__email", "listing__title")
    readonly_fields = (
        "id",
        "family",
        "listing",
        "provider",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)

    fieldsets = (
        (
            _("Subscription"),
            {"fields": ("id", "status", "cancelled_at")},
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
    def family_email(self, obj: MasterclassSubscription) -> str:
        return obj.family.email if obj.family_id else "—"

    @admin.display(description=_("Listing"))
    def listing_title(self, obj: MasterclassSubscription) -> str:
        return obj.listing.title if obj.listing_id else "—"
