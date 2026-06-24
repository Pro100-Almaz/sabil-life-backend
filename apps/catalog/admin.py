"""
Catalog admin — Phase 3: moderation actions, status badge, image preview,
list display improvements, fieldsets, and empty-value display.
"""

from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display

from apps.catalog.models import Listing, ListingStatus

# ---------------------------------------------------------------------------
# Bulk moderation actions
# ---------------------------------------------------------------------------

_MUTABLE_FOR_APPROVE = {ListingStatus.DRAFT, ListingStatus.PENDING}
_MUTABLE_FOR_REJECT = {
    ListingStatus.DRAFT,
    ListingStatus.PENDING,
    ListingStatus.ACTIVE,
}


@action(
    description=_("Approve selected listings (DRAFT/PENDING → ACTIVE)"),
    icon="check_circle",
)
def approve_listings(modeladmin, request, queryset):
    eligible = queryset.filter(status__in=_MUTABLE_FOR_APPROVE)
    skipped = queryset.exclude(status__in=_MUTABLE_FOR_APPROVE).count()
    updated = eligible.update(status=ListingStatus.ACTIVE)
    if updated:
        modeladmin.message_user(
            request,
            _("%(n)d listing(s) approved and set to ACTIVE.") % {"n": updated},
            messages.SUCCESS,
        )
    if skipped:
        modeladmin.message_user(
            request,
            _("%(n)d listing(s) skipped — only DRAFT/PENDING listings can be approved.")
            % {"n": skipped},
            messages.WARNING,
        )


@action(
    description=_("Reject selected listings (→ REJECTED)"),
    icon="cancel",
)
def reject_listings(modeladmin, request, queryset):
    eligible = queryset.filter(status__in=_MUTABLE_FOR_REJECT)
    skipped = queryset.exclude(status__in=_MUTABLE_FOR_REJECT).count()
    updated = eligible.update(status=ListingStatus.REJECTED)
    if updated:
        modeladmin.message_user(
            request,
            _("%(n)d listing(s) rejected.") % {"n": updated},
            messages.SUCCESS,
        )
    if skipped:
        msg = _("%(n)d listing(s) were already REJECTED — no change made.")
        modeladmin.message_user(
            request,
            msg % {"n": skipped},
            messages.WARNING,
        )


@action(description=_("Mark selected listings as featured"), icon="star")
def mark_featured(modeladmin, request, queryset):
    updated = queryset.update(is_featured=True)
    modeladmin.message_user(
        request,
        _("%(n)d listing(s) marked as featured.") % {"n": updated},
        messages.SUCCESS,
    )


@action(description=_("Unmark selected listings as featured"), icon="star_outline")
def unmark_featured(modeladmin, request, queryset):
    updated = queryset.update(is_featured=False)
    modeladmin.message_user(
        request,
        _("%(n)d listing(s) unmarked as featured.") % {"n": updated},
        messages.SUCCESS,
    )


# ---------------------------------------------------------------------------
# ListingAdmin
# ---------------------------------------------------------------------------


@admin.register(Listing)
class ListingAdmin(ModelAdmin):
    actions = [approve_listings, reject_listings, mark_featured, unmark_featured]

    # List view -----------------------------------------------------------
    list_display = (
        "title",
        "category",
        "status_badge",
        "neighborhood",
        "price_from_qar",
        "rating",
        "is_featured",
        "owner",
        "updated_at",
    )
    list_filter = ("status", "category", "is_featured", "neighborhood")
    search_fields = ("title", "subtitle", "neighborhood", "description")
    list_editable = ("is_featured",)
    list_per_page = 25
    empty_value_display = "—"

    # Detail form ---------------------------------------------------------
    readonly_fields = ("id", "created_at", "updated_at", "image_preview")

    fieldsets = (
        (
            _("Identity"),
            {"fields": ("id", "title", "subtitle", "category", "status", "is_featured")},
        ),
        (
            _("Location"),
            {"fields": ("neighborhood", "lat", "lng")},
        ),
        (
            _("Content"),
            {
                "fields": (
                    "description",
                    "highlights",
                    "age_groups",
                    "image_urls",
                    "image_preview",
                    "session_schedule",
                    "exact_address",
                    "materials_required",
                )
            },
        ),
        (
            _("Pricing & Stats"),
            {"fields": ("price_from_qar", "rating", "review_count")},
        ),
        (
            _("Ownership"),
            {"fields": ("owner", "created_at", "updated_at")},
        ),
    )

    # Custom columns ------------------------------------------------------

    @display(
        description=_("Status"),
        ordering="status",
        label={
            ListingStatus.ACTIVE: "success",
            ListingStatus.PENDING: "warning",
            ListingStatus.DRAFT: "info",
            ListingStatus.REJECTED: "danger",
        },
    )
    def status_badge(self, obj: Listing):
        return obj.status, obj.get_status_display()

    @admin.display(description=_("Images"))
    def image_preview(self, obj: Listing) -> str:
        urls = (obj.image_urls or [])[:3]
        if not urls:
            return "—"
        imgs = "".join(
            format_html(
                '<img src="{url}" style="'
                "height:60px;"
                "width:90px;"
                "object-fit:cover;"
                "border-radius:4px;"
                "margin-right:6px;"
                '"/>',
                url=url,
            )
            for url in urls
        )
        wrapper = '<div style="display:flex;flex-wrap:wrap;gap:4px;">{}</div>'
        return format_html(wrapper, imgs)
