from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action
from unfold.forms import AdminPasswordChangeForm

from apps.users.forms import CustomUserChangeForm, CustomUserCreationForm
from apps.users.models import CustomUser, Role


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


@admin.register(Role)
class RoleAdmin(ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class CustomUserAdmin(ModelAdmin, DjangoUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    change_password_form = AdminPasswordChangeForm
    model = CustomUser
    actions = [verify_providers]

    list_display = (
        "email",
        "full_name",
        "display_roles",
        "is_verified",
        "is_staff",
        "is_active",
    )
    list_filter = (
        "roles",
        "is_verified",
        "is_staff",
        "is_active",
    )
    search_fields = ("email", "full_name", "phone")
    ordering = ("email",)
    filter_horizontal = ("roles",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal info"),
            {"fields": ("full_name", "first_name", "last_name", "phone")},
        ),
        (
            _("Role & verification"),
            {"fields": ("roles", "is_verified")},
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
                    "roles",
                    "is_verified",
                    "is_staff",
                    "is_active",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
    )

    @admin.display(description=_("Roles"))
    def display_roles(self, obj: CustomUser) -> str:
        return ", ".join(obj.roles.values_list("name", flat=True)) or "-"


admin.site.register(CustomUser, CustomUserAdmin)
