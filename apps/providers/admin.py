from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from .models import ProviderProfile


@admin.register(ProviderProfile)
class ProviderProfileAdmin(ModelAdmin):
    list_display = (
        "user_email",
        "display_name",
        "is_verified_display",
        "hourly_rate_qar",
        "updated_at",
    )
    list_filter = ("user__is_verified", "user__role")
    search_fields = ("user__email", "display_name", "bio")
    readonly_fields = ("user", "created_at", "updated_at")

    fieldsets = (
        (
            _("Account"),
            {"fields": ("user", "display_name")},
        ),
        (
            _("Profile"),
            {"fields": ("bio", "subjects", "hourly_rate_qar", "availability")},
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(description=_("Email"), ordering="user__email")
    def user_email(self, obj: ProviderProfile) -> str:
        return obj.user.email

    @admin.display(description=_("Verified"), boolean=True, ordering="user__is_verified")
    def is_verified_display(self, obj: ProviderProfile) -> bool:
        return obj.user.is_verified
