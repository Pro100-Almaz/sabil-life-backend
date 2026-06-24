"""
Review views — Phase 7.

Endpoints:
  GET  /api/v1/listings/{listing_id}/reviews/  — public list (no auth)
  POST /api/v1/listings/{listing_id}/reviews/  — family only, engagement-gated
  GET  /api/v1/reviews/me/                     — own reviews (family)
  PATCH/DELETE /api/v1/reviews/{id}/           — own review only (family)
"""

import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Listing, ListingStatus

from apps.reviews.models import Review
from apps.reviews.permissions import IsFamily
from apps.reviews.schema import (
    LISTING_REVIEWS_CREATE_SCHEMA,
    LISTING_REVIEWS_LIST_SCHEMA,
    MY_REVIEWS_LIST_SCHEMA,
    REVIEW_DETAIL_SCHEMA,
)
from apps.reviews.serializers import (
    ReviewCreateSerializer,
    ReviewListSerializer,
    ReviewUpdateSerializer,
)

logger = logging.getLogger(__name__)


class ListingReviewsView(APIView):
    """
    GET  — public list of reviews for a listing (no auth required).
    POST — family creates a review (auth + role=FAMILY required).
    """

    # Hint for drf-spectacular schema generation
    serializer_class = ReviewListSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsFamily()]
        return [permissions.AllowAny()]

    @extend_schema(**LISTING_REVIEWS_LIST_SCHEMA)
    def get(self, request, listing_id, version=None):
        listing = get_object_or_404(Listing, pk=listing_id, status=ListingStatus.ACTIVE)
        qs = listing.reviews.select_related("author").order_by("-created_at")

        # Manual pagination using DRF's default paginator
        paginator = self._get_paginator()
        page = paginator.paginate_queryset(qs, request, view=self)
        if page is not None:
            serializer = ReviewListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ReviewListSerializer(qs, many=True)
        return Response(serializer.data)

    def _get_paginator(self):
        from rest_framework.pagination import PageNumberPagination

        paginator = PageNumberPagination()
        paginator.page_size = 20
        return paginator

    @extend_schema(**LISTING_REVIEWS_CREATE_SCHEMA)
    def post(self, request, listing_id, version=None):
        listing = get_object_or_404(Listing, pk=listing_id, status=ListingStatus.ACTIVE)

        serializer = ReviewCreateSerializer(
            data=request.data,
            context={"request": request, "listing": listing},
        )
        if not serializer.is_valid():
            # Detect the duplicate-review case to return 409
            errors = serializer.errors
            non_field = errors.get("non_field_errors", [])
            if any("already reviewed" in str(e) for e in non_field):
                return Response(errors, status=status.HTTP_409_CONFLICT)
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            review = serializer.save()
        except Exception:
            # Fallback: IntegrityError that slipped through validate()
            return Response(
                {"non_field_errors": ["You have already reviewed this listing."]},
                status=status.HTTP_409_CONFLICT,
            )

        logger.info(
            "Family %s posted review %s on listing %s.",
            request.user.email,
            review.id,
            listing_id,
        )
        return Response(ReviewListSerializer(review).data, status=status.HTTP_201_CREATED)


class MyReviewsView(generics.ListAPIView):
    """GET /api/v1/reviews/me/ — list own reviews across all listings."""

    serializer_class = ReviewListSerializer
    permission_classes = [permissions.IsAuthenticated, IsFamily]
    # Prevents drf-spectacular from calling get_queryset() without a real user
    queryset = Review.objects.none()

    @extend_schema(**MY_REVIEWS_LIST_SCHEMA)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return (
            Review.objects.filter(author=self.request.user)
            .select_related("author")
            .order_by("-created_at")
        )


class ReviewDetailView(APIView):
    """
    PATCH  /api/v1/reviews/{id}/ — update own review.
    DELETE /api/v1/reviews/{id}/ — delete own review.

    Returns 404 (not 403) when the review exists but belongs to another user,
    so as not to leak existence information.
    """

    permission_classes = [permissions.IsAuthenticated, IsFamily]
    # Hint for drf-spectacular schema generation
    serializer_class = ReviewUpdateSerializer

    def _get_own_review(self, request, id):
        return get_object_or_404(Review, pk=id, author=request.user)

    @extend_schema(**REVIEW_DETAIL_SCHEMA)
    def patch(self, request, id, version=None):
        review = self._get_own_review(request, id)
        serializer = ReviewUpdateSerializer(review, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        logger.info("Family %s updated review %s.", request.user.email, id)
        return Response(ReviewListSerializer(review).data)

    @extend_schema(**REVIEW_DETAIL_SCHEMA)
    def delete(self, request, id, version=None):
        review = self._get_own_review(request, id)
        review.delete()
        logger.info("Family %s deleted review %s.", request.user.email, id)
        return Response(status=status.HTTP_204_NO_CONTENT)
