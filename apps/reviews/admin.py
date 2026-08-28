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
from django.db.models import Count
from unfold.admin import ModelAdmin
from unfold.decorators import display

from apps.reviews.models import Review, TutorReview


class ReportPriorityAdmin(ModelAdmin):
    @display(description="Reports", ordering="_report_count")
    def report_count(self, obj) -> int:
        return obj._report_count

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(_report_count=Count("reports"))
            .order_by("-_report_count", "-created_at")
        )


@admin.register(Review)
class ReviewAdmin(ReportPriorityAdmin):
    list_display = (
        "listing_title",
        "author_email",
        "rating",
        "report_count",
        "created_at",
    )
    list_filter = ("rating", "listing__category")
    search_fields = ("listing__title", "author__email", "text")
    readonly_fields = ("id", "listing", "author", "created_at", "updated_at")

    def listing_title(self, obj: Review) -> str:
        return obj.listing.title if obj.listing_id else "—"

    listing_title.short_description = "Listing"
    listing_title.admin_order_field = "listing__title"

    def author_email(self, obj: Review) -> str:
        return obj.author.email if obj.author_id else "—"

    author_email.short_description = "Author"
    author_email.admin_order_field = "author__email"


@admin.register(TutorReview)
class TutorReviewAdmin(ReportPriorityAdmin):
    list_display = (
        "tutor_name",
        "author_email",
        "rating",
        "report_count",
        "created_at",
    )
    list_filter = ("rating",)
    search_fields = ("tutor__user__full_name", "author__email", "text")
    readonly_fields = ("id", "tutor", "author", "created_at", "updated_at")

    @admin.display(description="Tutor", ordering="tutor__user__full_name")
    def tutor_name(self, obj: TutorReview) -> str:
        return obj.tutor.user.full_name or obj.tutor.user.email

    @admin.display(description="Author", ordering="author__email")
    def author_email(self, obj: TutorReview) -> str:
        return obj.author.email
