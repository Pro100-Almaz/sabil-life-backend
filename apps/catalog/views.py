import logging

from django.db.models import Count, QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from apps.catalog.filters import ListingFilter
from apps.providers.models import TutorDetail, TutorSubject

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.catalog.schema import (
    CATEGORIES_SCHEMA,
    LISTING_DETAIL_SCHEMA,
    LISTING_LIST_PARAMETERS,
    LISTING_LIST_SCHEMA,
)
from apps.catalog.serializers import (
    CategoryCountSerializer,
    ListingCardSerializer,
    ListingDetailSerializer,
    TutorCardSerializer,
)
from apps.catalog.services import annotate_distance_km

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="List active listings",
        parameters=LISTING_LIST_PARAMETERS,
        responses=LISTING_LIST_SCHEMA,
    ),
    retrieve=extend_schema(
        summary="Retrieve listing detail",
        responses=LISTING_DETAIL_SCHEMA,
    ),
)
class ListingViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public read-only ViewSet for Listing.

    list:   GET /api/v1/listings/
    detail: GET /api/v1/listings/{id}/

    Only ACTIVE listings are returned.  Distance annotation (haversine) is
    added when the caller supplies valid lat + lng query params.  Sort order
    is controlled by the ?sort= param; the default Meta ordering applies when
    sort is absent or unrecognised.
    """

    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ListingFilter
    lookup_field = "id"
    # Allow DRF OrderingFilter on explicit model fields if needed in future;
    # the custom ?sort= logic below takes precedence.
    ordering_fields = ["rating", "price_from_qar", "created_at"]

    def get_queryset(self) -> QuerySet:
        qs = Listing.objects.filter(status=ListingStatus.ACTIVE)

        # ------------------------------------------------------------------
        # Distance annotation
        # ------------------------------------------------------------------
        lat_str = self.request.query_params.get("lat")
        lng_str = self.request.query_params.get("lng")
        lat: float | None = None
        lng: float | None = None

        if lat_str is not None and lng_str is not None:
            try:
                lat = float(lat_str)
                lng = float(lng_str)
                qs = annotate_distance_km(qs, lat, lng)
            except (TypeError, ValueError):
                logger.debug(
                    "Invalid lat/lng params (%s, %s) — distance not annotated.",
                    lat_str,
                    lng_str,
                )

        # ------------------------------------------------------------------
        # Max-distance radius filter (only meaningful after annotation)
        # ------------------------------------------------------------------
        max_dist_str = self.request.query_params.get("max_distance_km")
        if max_dist_str is not None and lat is not None:
            try:
                max_dist = float(max_dist_str)
                qs = qs.filter(distance_km__lte=max_dist)
            except (TypeError, ValueError):
                pass

        # ------------------------------------------------------------------
        # Sort
        # ------------------------------------------------------------------
        sort = self.request.query_params.get("sort")
        if sort == "distance":
            if lat is not None:
                # NULLs last: listings without coordinates sort to the bottom
                qs = qs.order_by("distance_km", "-is_featured")
            else:
                # lat/lng absent — silently fall back to default ordering
                logger.debug("?sort=distance requested without lat/lng — ignored.")
        elif sort == "rating":
            qs = qs.order_by("-rating", "-review_count")
        elif sort == "price_low":
            qs = qs.order_by("price_from_qar")
        # Default: model Meta ordering (-is_featured, -created_at) applies.

        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ListingDetailSerializer
        return ListingCardSerializer


@extend_schema(
    summary="List all categories with ACTIVE listing counts",
    responses=CATEGORIES_SCHEMA,
)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def categories_view(request: Request) -> Response:
    """
    GET /api/v1/categories/

    Returns all ListingCategory choices, each with the count of ACTIVE listings.
    Zero-count categories are always included so the frontend can render empty tabs.
    """
    # Aggregate counts for ACTIVE listings only
    counts: dict[str, int] = dict(
        Listing.objects.filter(status=ListingStatus.ACTIVE)
        .values_list("category")
        .annotate(cnt=Count("id"))
        .values_list("category", "cnt")
    )

    data = [
        {"key": key, "count": counts.get(key, 0)}
        for key, _label in ListingCategory.choices
    ]

    serializer = CategoryCountSerializer(data, many=True)
    return Response(serializer.data)


class TutorListViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = TutorCardSerializer

    def get_queryset(self):
        return (
            TutorDetail.objects
            .select_related("user")
            .filter(user__role="TUTOR", is_verified=True)
            .order_by("-rating", "-review_count")
        )


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def tutor_subjects_view(request: Request) -> Response:
    names = list(TutorSubject.objects.values_list("name", flat=True))
    return Response(names)
