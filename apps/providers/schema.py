"""
drf-spectacular OpenAPI schema helpers for the providers app.

Mirrors the pattern in apps/users/schema.py and apps/catalog/schema.py.
"""

from drf_spectacular.utils import OpenApiExample, OpenApiResponse

from apps.core.schema import UNAUTHORIZED_EXAMPLES, ErrorResponseSerializer

from .serializers import ProviderListingSerializer, ProviderProfileSerializer

# ---------------------------------------------------------------------------
# Reusable example values
# ---------------------------------------------------------------------------

_PROFILE_EXAMPLE = {
    "user_id": 7,
    "email": "tutor@example.com",
    "full_name": "Ahmed Al-Mansoori",
    "role": "TUTOR",
    "is_verified": True,
    "display_name": "Ahmed Maths Tutoring",
    "bio": "10 years teaching secondary school mathematics in Doha.",
    "subjects": ["Math", "Physics"],
    "hourly_rate_qar": 150,
    "availability": "Weekday evenings, weekend mornings",
    "created_at": "2026-01-15T08:00:00Z",
    "updated_at": "2026-06-01T12:00:00Z",
}

_LISTING_EXAMPLE = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "IGCSE Maths Tutoring — West Bay",
    "category": "TUTORING",
    "subtitle": "Small groups and 1-to-1 sessions",
    "neighborhood": "West Bay, Doha",
    "lat": 25.369,
    "lng": 51.551,
    "price_from_qar": 150,
    "age_groups": ["12-16", "16-18"],
    "image_urls": ["https://picsum.photos/seed/tutor1/400/300"],
    "description": "Personalised maths tutoring for IGCSE and A-Level students.",
    "highlights": ["Small groups", "Weekend slots", "Native Arabic speakers"],
    "is_featured": False,
    "rating": "0.0",
    "review_count": 0,
    "status": "PENDING",
    "owner_id": "7",
    "created_at": "2026-06-01T10:00:00Z",
    "updated_at": "2026-06-01T10:00:00Z",
}

_FORBIDDEN_EXAMPLE = [
    OpenApiExample(
        "Not a provider",
        value={
            "detail": (
                "You must be a provider (TUTOR or MASTERCLASS) to access this resource."
            )
        },
        status_codes=["403"],
    )
]

_CATEGORY_MISMATCH_EXAMPLE = [
    OpenApiExample(
        "Category mismatch",
        value={"category": ["TUTOR providers can only create TUTORING listings."]},
        status_codes=["400"],
    )
]

# ---------------------------------------------------------------------------
# Profile endpoint schemas
# ---------------------------------------------------------------------------

PROVIDER_PROFILE_GET_SCHEMA = {
    "summary": "Get own provider profile",
    "description": (
        "Returns the authenticated provider's profile. "
        "Auto-creates the profile if it doesn't exist yet (lazy-create on first access)."
    ),
    "responses": {
        200: OpenApiResponse(
            response=ProviderProfileSerializer,
            description="Provider profile data.",
            examples=[
                OpenApiExample(
                    "Profile",
                    value=_PROFILE_EXAMPLE,
                    status_codes=["200"],
                )
            ],
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Authentication required.",
            examples=UNAUTHORIZED_EXAMPLES,
        ),
        403: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="User is not a provider.",
            examples=_FORBIDDEN_EXAMPLE,
        ),
    },
}

PROVIDER_PROFILE_PATCH_SCHEMA = {
    "summary": "Update own provider profile",
    "description": (
        "Partial update of the authenticated provider's profile. "
        "is_verified is read-only; only admins may change it via the User model."
    ),
    "responses": {
        200: OpenApiResponse(
            response=ProviderProfileSerializer,
            description="Updated provider profile.",
            examples=[
                OpenApiExample(
                    "Updated profile",
                    value={**_PROFILE_EXAMPLE, "display_name": "Ahmed Advanced Maths"},
                    status_codes=["200"],
                )
            ],
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Validation error.",
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Authentication required.",
            examples=UNAUTHORIZED_EXAMPLES,
        ),
        403: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="User is not a provider.",
            examples=_FORBIDDEN_EXAMPLE,
        ),
    },
}

# ---------------------------------------------------------------------------
# Listing endpoint schemas
# ---------------------------------------------------------------------------

PROVIDER_LISTING_LIST_SCHEMA = {
    "summary": "List own listings",
    "description": (
        "Returns all listings owned by the authenticated provider (any status)."
    ),
    "responses": {
        200: OpenApiResponse(
            response=ProviderListingSerializer(many=True),
            description="Provider's listings.",
            examples=[
                OpenApiExample(
                    "Listings",
                    value={
                        "count": 1,
                        "next": None,
                        "previous": None,
                        "results": [_LISTING_EXAMPLE],
                    },
                    status_codes=["200"],
                )
            ],
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Authentication required.",
            examples=UNAUTHORIZED_EXAMPLES,
        ),
        403: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="User is not a provider.",
            examples=_FORBIDDEN_EXAMPLE,
        ),
    },
}

PROVIDER_LISTING_CREATE_SCHEMA = {
    "summary": "Create a listing",
    "description": (
        "Create a new listing owned by the authenticated provider.\n\n"
        "**Category constraint:**\n"
        "- TUTOR role → category must be `TUTORING`.\n"
        "- MASTERCLASS role → category must be `MASTERCLASSES`.\n\n"
        "**Status rule:** `status` in the request body is ignored. "
        "The server sets:\n"
        "- `PENDING` if the provider is verified (awaiting admin approval).\n"
        "- `DRAFT` if the provider is not yet verified.\n\n"
        "`owner` in the request body is also ignored — always set to the caller."
    ),
    "responses": {
        201: OpenApiResponse(
            response=ProviderListingSerializer,
            description="Listing created.",
            examples=[
                OpenApiExample(
                    "Created listing",
                    value=_LISTING_EXAMPLE,
                    status_codes=["201"],
                )
            ],
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Validation error — e.g. category mismatch.",
            examples=_CATEGORY_MISMATCH_EXAMPLE,
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Authentication required.",
            examples=UNAUTHORIZED_EXAMPLES,
        ),
        403: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="User is not a provider.",
            examples=_FORBIDDEN_EXAMPLE,
        ),
    },
}

PROVIDER_LISTING_RETRIEVE_SCHEMA = {
    "summary": "Retrieve own listing",
    "description": (
        "Returns a single listing owned by the authenticated provider. "
        "Returns 404 if the listing doesn't exist or belongs to another provider."
    ),
    "responses": {
        200: OpenApiResponse(
            response=ProviderListingSerializer,
            description="Listing detail.",
            examples=[
                OpenApiExample(
                    "Listing detail",
                    value=_LISTING_EXAMPLE,
                    status_codes=["200"],
                )
            ],
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Authentication required.",
            examples=UNAUTHORIZED_EXAMPLES,
        ),
        403: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="User is not a provider.",
            examples=_FORBIDDEN_EXAMPLE,
        ),
        404: OpenApiResponse(
            description="Listing not found or not owned by this provider.",
            examples=[
                OpenApiExample(
                    "Not found",
                    value={"detail": "No Listing matches the given query."},
                    status_codes=["404"],
                )
            ],
        ),
    },
}

PROVIDER_LISTING_UPDATE_SCHEMA = {
    "summary": "Update own listing (PATCH)",
    "description": (
        "Partial update of an owned listing. "
        "Status is recalculated server-side on every update "
        "(PENDING if verified, DRAFT if not). "
        "Category changes are validated against the provider's role."
    ),
    "responses": {
        200: OpenApiResponse(
            response=ProviderListingSerializer,
            description="Updated listing.",
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Validation error.",
            examples=_CATEGORY_MISMATCH_EXAMPLE,
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Authentication required.",
            examples=UNAUTHORIZED_EXAMPLES,
        ),
        403: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="User is not a provider.",
            examples=_FORBIDDEN_EXAMPLE,
        ),
        404: OpenApiResponse(
            description="Listing not found or not owned by this provider.",
        ),
    },
}

PROVIDER_LISTING_DESTROY_SCHEMA = {
    "summary": "Delete own listing",
    "description": (
        "Hard-deletes an owned listing. This action is permanent. "
        "Returns 404 if the listing doesn't exist or belongs to another provider. "
        "Note: Phase 5 inquiries will use on_delete=PROTECT on the listing FK, "
        "so a listing with active inquiries cannot be deleted until Phase 5 "
        "handles that constraint."
    ),
    "responses": {
        204: OpenApiResponse(description="Listing deleted."),
        401: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Authentication required.",
            examples=UNAUTHORIZED_EXAMPLES,
        ),
        403: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="User is not a provider.",
            examples=_FORBIDDEN_EXAMPLE,
        ),
        404: OpenApiResponse(
            description="Listing not found or not owned by this provider.",
        ),
    },
}
