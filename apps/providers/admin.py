from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from .models import ProviderProfile, TutorDetail, TutorSubject


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


@admin.register(TutorDetail)
class TutorDetailAdmin(ModelAdmin):
    list_display = (
        "user_email",
        "user_full_name",
        "rating",
        "review_count",
        "price_per_hour_qar",
        "trial_available",
    )
    list_filter = ("trial_available", "languages")
    search_fields = ("user__email", "user__full_name", "credentials", "bio")
    readonly_fields = ("user", "created_at", "updated_at")

    @admin.display(description=_("Email"), ordering="user__email")
    def user_email(self, obj: TutorDetail) -> str:
        return obj.user.email

    @admin.display(description=_("Name"), ordering="user__full_name")
    def user_full_name(self, obj: TutorDetail) -> str:
        return obj.user.full_name


@admin.register(TutorSubject)
class TutorSubjectAdmin(ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
