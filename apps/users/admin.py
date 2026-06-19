from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action
from unfold.forms import AdminPasswordChangeForm

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import CustomUser


@action(
    description=_("Verify selected providers (set is_verified=True)"),
    icon="verified",
)
def verify_providers(modeladmin, request, queryset):
    updated = queryset.update(is_verified=True)
    modeladmin.message_user(
        request,
        _("%(count)d user(s) marked as verified.") % {"count": updated},
        messages.SUCCESS,
    )


class CustomUserAdmin(ModelAdmin, DjangoUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    change_password_form = AdminPasswordChangeForm
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
