"""
Catalog admin — Phase 2: minimal registration only.
Phase 3 will add moderation actions (approve / reject), inline review display,
map preview, and image thumbnail columns.
"""

from django.contrib import admin

from .models import Listing


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "status",
        "neighborhood",
        "is_featured",
        "owner",
        "updated_at",
    )
    list_filter = ("status", "category", "is_featured")
    search_fields = ("title", "subtitle", "neighborhood")
    readonly_fields = ("id", "created_at", "updated_at")
