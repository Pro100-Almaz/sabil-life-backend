"""
Catalog admin — Phase 3: moderation actions, status badge, image preview,
list display improvements, fieldsets, and empty-value display.
"""

import uuid
from pathlib import Path

from django import forms
from django.contrib import admin, messages
from django.core.files.storage import default_storage
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


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    widget = MultipleImageInput

    def clean(self, data, initial=None):
        single_clean = super().clean
        if not data:
            return []
        if isinstance(data, (list, tuple)):
            return [single_clean(item, initial) for item in data]
        return [single_clean(data, initial)]


class ListingAdminForm(forms.ModelForm):
    uploaded_images = MultipleImageField(required=False, label=_("Upload images"))

    class Meta:
        model = Listing
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["uploaded_images"].widget.attrs.update(
            {"multiple": True, "accept": "image/*"}
        )


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
    form = ListingAdminForm
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
                    "uploaded_images",
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

    def save_model(self, request, obj: Listing, form: ListingAdminForm, change: bool) -> None:
        super().save_model(request, obj, form, change)

        uploaded_images = request.FILES.getlist("uploaded_images") or []
        if not uploaded_images:
            return

        image_urls = list(obj.image_urls or [])
        for uploaded_image in uploaded_images:
            suffix = Path(uploaded_image.name).suffix.lower()
            object_name = f"listings/{obj.id}/{uuid.uuid4().hex}{suffix}"
            saved_name = default_storage.save(object_name, uploaded_image)
            image_urls.append(default_storage.url(saved_name))

        obj.image_urls = image_urls
        obj.save(update_fields=["image_urls", "updated_at"])
