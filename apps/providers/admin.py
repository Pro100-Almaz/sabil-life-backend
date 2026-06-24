from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from .models import ProviderVerification, TutorDetail, TutorSubject


@admin.register(TutorDetail)
class TutorDetailAdmin(ModelAdmin):
    list_display = (
        "user_email",
        "user_full_name",
        "is_verified",
        "rating",
        "review_count",
        "price_per_hour_qar",
        "trial_available",
    )
    list_filter = ("is_verified", "trial_available", "languages")
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


@admin.register(ProviderVerification)
class ProviderVerificationAdmin(ModelAdmin):
    list_display = (
        "user_email",
        "provider_type",
        "status",
        "updated_at",
    )
    list_filter = ("status", "provider_type")
    search_fields = ("user__email", "user__full_name", "comment")
    readonly_fields = ("user", "provider_type", "created_at", "updated_at")

    @admin.display(description=_("Email"), ordering="user__email")
    def user_email(self, obj: ProviderVerification) -> str:
        return obj.user.email
