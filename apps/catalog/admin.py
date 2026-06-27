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

from unfold.admin import ModelAdmin, TabularInline   # unfold-styled inline

from apps.catalog.models import Listing, ListingImage, ListingStatus
from apps.catalog.services import delete_listing, delete_listing_image
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

class ListingImageInline(TabularInline):
    model = ListingImage
    extra = 0 
    fields = ("thumb", "key", "position")
    readonly_fields = ("thumb", "key")
    ordering = ("position", "created_at")

    @admin.display(description=_("Preview"))
    def thumb(self, obj: ListingImage) -> str:
        if not obj.key:
            return "-"
        return format_html(
            '<img src="{}" style="height:60px;width:90px;'
            'object-fit:cover;border-radius:4px;"/>',
            default_storage.url(obj.key),
        )

@admin.register(Listing)
class ListingAdmin(ModelAdmin):
    form = ListingAdminForm
    inlines = [ListingImageInline]
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
    readonly_fields = ("id", "created_at", "updated_at")

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

    def save_model(self, request, obj: Listing, form: ListingAdminForm, change: bool) -> None:
        super().save_model(request, obj, form, change)

        uploaded_images = request.FILES.getlist("uploaded_images") or []
        if not uploaded_images:
            return

        start = obj.images.count()
        for i, uploaded_image in enumerate(uploaded_images):
            suffix = Path(uploaded_image.name).suffix.lower()
            object_name = f"listings/{obj.id}/{uuid.uuid4().hex}{suffix}"
            key = default_storage.save(object_name, uploaded_image)
            ListingImage.objects.create(listing=obj, key=key, position=start + i)

    def save_formset(self, request, form, formset, change):
        if formset.model is ListingImage:
            instances = formset.save(commit=False)
            for obj in formset.deleted_objects:
                delete_listing_image(obj)
            for instance in instances:
                instance.save()

            formset.save_m2m()
        else:
            super().save_formset(request, form, formset, change)

    def delete_model(self, request, obj):
        delete_listing(obj)

    def delete_queryset(self, request, queryset):
        for listing in queryset:
            delete_listing(listing)