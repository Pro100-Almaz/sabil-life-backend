"""
ServiceSuggestion admin — Phase 5.

Admin-only management of family service suggestions. No REST endpoints.
Bulk actions: mark_reviewed, mark_acted_on, mark_dismissed.
admin_notes is editable by admin only (writable field in the form, never in API).
"""

from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action

from .models import ServiceSuggestion, SuggestionStatus

# ---------------------------------------------------------------------------
# Bulk actions
# ---------------------------------------------------------------------------


@action(description=_("Mark selected suggestions as Reviewed"), icon="visibility")
def mark_reviewed(modeladmin, request, queryset):
    updated = queryset.exclude(status=SuggestionStatus.REVIEWED).update(
        status=SuggestionStatus.REVIEWED
    )
    modeladmin.message_user(
        request,
        _("%(n)d suggestion(s) marked as Reviewed.") % {"n": updated},
        messages.SUCCESS,
    )


@action(description=_("Mark selected suggestions as Acted on"), icon="task_alt")
def mark_acted_on(modeladmin, request, queryset):
    updated = queryset.exclude(status=SuggestionStatus.ACTED_ON).update(
        status=SuggestionStatus.ACTED_ON
    )
    modeladmin.message_user(
        request,
        _("%(n)d suggestion(s) marked as Acted on.") % {"n": updated},
        messages.SUCCESS,
    )


@action(description=_("Mark selected suggestions as Dismissed"), icon="block")
def mark_dismissed(modeladmin, request, queryset):
    updated = queryset.exclude(status=SuggestionStatus.DISMISSED).update(
        status=SuggestionStatus.DISMISSED
    )
    modeladmin.message_user(
        request,
        _("%(n)d suggestion(s) marked as Dismissed.") % {"n": updated},
        messages.SUCCESS,
    )


# ---------------------------------------------------------------------------
# Admin class
# ---------------------------------------------------------------------------


@admin.register(ServiceSuggestion)
class ServiceSuggestionAdmin(ModelAdmin):
    actions = [mark_reviewed, mark_acted_on, mark_dismissed]

    list_display = (
        "created_at",
        "family_email",
        "category",
        "neighborhood",
        "message_preview",
        "status",
    )
    list_filter = ("status", "category")
    search_fields = ("family__email", "message", "neighborhood", "admin_notes")
    ordering = ("-created_at",)

    # Admins may only edit status and admin_notes — everything else is read-only.
    readonly_fields = (
        "id",
        "family",
        "category",
        "neighborhood",
        "message",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            _("Suggestion"),
            {
                "fields": (
                    "id",
                    "family",
                    "category",
                    "neighborhood",
                    "message",
                    "created_at",
                )
            },
        ),
        (
            _("Admin"),
            {"fields": ("status", "admin_notes", "updated_at")},
        ),
    )

    @admin.display(description=_("Family email"))
    def family_email(self, obj: ServiceSuggestion) -> str:
        return obj.family.email if obj.family_id else "—"

    @admin.display(description=_("Message preview"))
    def message_preview(self, obj: ServiceSuggestion) -> str:
        return obj.message[:80]
