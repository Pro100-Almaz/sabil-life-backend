"""
drf-spectacular OpenAPI schema helpers for the catalog app.

Mirrors the pattern established in apps/users/schema.py:
- response dict constants used with @extend_schema / @extend_schema_view
- OpenApiParameter list for query params on the list endpoint
"""

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiTypes,
)

from .serializers import (
    CategoryCountSerializer,
    ListingCardSerializer,
    ListingDetailSerializer,
)

# ---------------------------------------------------------------------------
# Reusable example values
# ---------------------------------------------------------------------------

_LISTING_CARD_EXAMPLE = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Bright Minds Tutoring",
    "category": "TUTORING",
    "subtitle": "Expert maths and science tuition",
    "neighborhood": "West Bay, Doha",
    "lat": 25.369,
    "lng": 51.551,
    "rating": "4.8",
    "review_count": 24,
    "price_from_qar": 150,
    "image_urls": ["https://picsum.photos/seed/bmt/400/300"],
    "age_groups": ["8-12", "12-16"],
    "is_featured": True,
    "distance_km": 1.23,
}

_LISTING_DETAIL_EXAMPLE = {
    **_LISTING_CARD_EXAMPLE,
    "description": "Personalised tutoring sessions covering all core subjects.",
    "highlights": ["Small groups", "Weekend slots", "Native Arabic speakers"],
    "owner_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "reviews": [],
}

_CATEGORY_EXAMPLE = [
    {"key": "SCHOOLS", "count": 4},
    {"key": "NURSERIES", "count": 3},
    {"key": "ACTIVITIES", "count": 6},
    {"key": "ENTERTAINMENT", "count": 3},
    {"key": "TUTORING", "count": 3},
    {"key": "MASTERCLASSES", "count": 3},
    {"key": "PARTNERSHIPS", "count": 2},
]

# ---------------------------------------------------------------------------
# List endpoint — query parameter documentation
# ---------------------------------------------------------------------------

LISTING_LIST_PARAMETERS = [
    OpenApiParameter(
        name="category",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description=(
            "Filter by category. Case-insensitive. "
            "One of: SCHOOLS, NURSERIES, ACTIVITIES, ENTERTAINMENT, "
            "TUTORING, MASTERCLASSES, PARTNERSHIPS."
        ),
        required=False,
        examples=[
            OpenApiExample("Tutoring", value="TUTORING"),
            OpenApiExample("Schools (lowercase)", value="schools"),
        ],
    ),
    OpenApiParameter(
        name="q",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description="Free-text search over title and subtitle (case-insensitive OR).",
        required=False,
    ),
    OpenApiParameter(
        name="price_max",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description="Return only listings with price_from_qar ≤ this value.",
        required=False,
    ),
    OpenApiParameter(
        name="age",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description=(
            "Return listings whose age_groups list contains this exact string. "
            'Example: ?age=5-8 matches listings with "5-8" in their age_groups.'
        ),
        required=False,
    ),
    OpenApiParameter(
        name="lat",
        type=OpenApiTypes.FLOAT,
        location=OpenApiParameter.QUERY,
        description=(
            "User latitude (decimal degrees). Required together with lng to "
            "enable distance annotation and ?sort=distance / ?max_distance_km."
        ),
        required=False,
    ),
    OpenApiParameter(
        name="lng",
        type=OpenApiTypes.FLOAT,
        location=OpenApiParameter.QUERY,
        description="User longitude (decimal degrees). Required together with lat.",
        required=False,
    ),
    OpenApiParameter(
        name="max_distance_km",
        type=OpenApiTypes.FLOAT,
        location=OpenApiParameter.QUERY,
        description=(
            "Exclude listings further than this many km from the provided lat/lng. "
            "Requires lat and lng."
        ),
        required=False,
    ),
    OpenApiParameter(
        name="sort",
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
        description=(
            "Sort order. Options: distance (requires lat+lng), "
            "rating (highest first), price_low (cheapest first). "
            "Default: featured first, then newest."
        ),
        required=False,
        examples=[
            OpenApiExample("By distance", value="distance"),
            OpenApiExample("By rating", value="rating"),
            OpenApiExample("By price", value="price_low"),
        ],
    ),
    OpenApiParameter(
        name="page",
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description="Page number for pagination (page size: 20).",
        required=False,
    ),
]

# ---------------------------------------------------------------------------
# Response schema constants
# ---------------------------------------------------------------------------

LISTING_LIST_SCHEMA = {
    200: OpenApiResponse(
        response=ListingCardSerializer(many=True),
        description="Paginated list of active listings.",
        examples=[
            OpenApiExample(
                "Listing list",
                value={
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [_LISTING_CARD_EXAMPLE],
                },
                status_codes=["200"],
            )
        ],
    ),
}

LISTING_DETAIL_SCHEMA = {
    200: OpenApiResponse(
        response=ListingDetailSerializer,
        description="Full listing detail including description, highlights, and reviews.",
        examples=[
            OpenApiExample(
                "Listing detail",
                value=_LISTING_DETAIL_EXAMPLE,
                status_codes=["200"],
            )
        ],
    ),
    404: OpenApiResponse(
        description="Listing not found or not ACTIVE.",
        examples=[
            OpenApiExample(
                "Not found",
                value={"detail": "No Listing matches the given query."},
                status_codes=["404"],
            )
        ],
    ),
}

CATEGORIES_SCHEMA = {
    200: OpenApiResponse(
        response=CategoryCountSerializer(many=True),
        description=(
            "All listing categories with the count of ACTIVE listings in each. "
            "Zero-count categories are always included so the frontend can render "
            "empty tabs."
        ),
        examples=[
            OpenApiExample(
                "Categories",
                value=_CATEGORY_EXAMPLE,
                status_codes=["200"],
            )
        ],
    ),
}
