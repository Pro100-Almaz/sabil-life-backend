from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import CustomUser


@admin.action(description=_("Verify selected providers (set is_verified=True)"))
def verify_providers(modeladmin, request, queryset):
    """
    Bulk-set is_verified=True on selected users.
    Meaningful only for TUTOR/MASTERCLASS roles; harmless for others.
    """
    updated = queryset.update(is_verified=True)
    modeladmin.message_user(
        request,
        _("%(count)d user(s) marked as verified.") % {"count": updated},
        messages.SUCCESS,
    )


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    actions = [verify_providers]

    list_display = (
        "email",
        "full_name",
        "role",
        "is_verified",
        "is_staff",
        "is_active",
    )
    list_filter = (
        "role",
        "is_verified",
        "is_staff",
        "is_active",
    )
    search_fields = ("email", "full_name", "phone")
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal info"),
            {"fields": ("full_name", "first_name", "last_name", "phone")},
        ),
        (
            _("Role & verification"),
            {"fields": ("role", "is_verified")},
        ),
        (
            _("Location"),
            {"fields": ("home_lat", "home_lng")},
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_staff",
                    "is_active",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "full_name",
                    "role",
                    "is_verified",
                    "is_staff",
                    "is_active",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
    )


admin.site.register(CustomUser, CustomUserAdmin)
