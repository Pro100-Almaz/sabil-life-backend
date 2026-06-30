"""
Review URL patterns — Phase 7.

Mounted at the api/v1/ prefix level in conf/urls.py.
"""

from django.urls import path

from apps.reviews.views import (
    ListingReviewsView,
    MyReviewsView,
    ReviewDetailView,
    TutorReviewDetailView,
    TutorReviewsView,
)

urlpatterns = [
    path(
        "listings/<uuid:listing_id>/reviews/",
        ListingReviewsView.as_view(),
        name="listing-reviews",
    ),
    path(
        "tutors/<int:tutor_id>/reviews/",
        TutorReviewsView.as_view(),
        name="tutor-reviews",
    ),
    path(
        "tutor-reviews/<uuid:review_id>/",
        TutorReviewDetailView.as_view(),
        name="tutor-review-detail",
    ),
    path(
        "reviews/me/",
        MyReviewsView.as_view(),
        name="my-reviews",
    ),
    path(
        "reviews/<uuid:review_id>/",
        ReviewDetailView.as_view(),
        name="review-detail",
    ),
]
