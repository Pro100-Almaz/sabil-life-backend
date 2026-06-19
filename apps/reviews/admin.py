"""
Review admin — Phase 7.

Admin users can view and delete reviews. Authorship fields (listing, author)
are read-only to prevent tampering with the review's provenance.

The bulk delete action uses Django's default `delete_selected`. The
post_delete signal fires for each deleted instance (Django's delete()
method triggers signals; bulk QuerySet.delete() also fires post_delete
per instance when using the default manager), so rating recompute fires.
"""

from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("listing_title", "author_email", "rating", "created_at")
    list_filter = ("rating", "listing__category")
    search_fields = ("listing__title", "author__email", "text")
    readonly_fields = ("id", "listing", "author", "created_at", "updated_at")
    ordering = ("-created_at",)

    def listing_title(self, obj: Review) -> str:
        return obj.listing.title if obj.listing_id else "—"

    listing_title.short_description = "Listing"
    listing_title.admin_order_field = "listing__title"

    def author_email(self, obj: Review) -> str:
        return obj.author.email if obj.author_id else "—"

    author_email.short_description = "Author"
    author_email.admin_order_field = "author__email"
