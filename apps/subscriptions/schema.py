"""
drf-spectacular OpenAPI schema helpers for the subscriptions app.
"""

from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse

from apps.core.schema import UNAUTHORIZED_EXAMPLES, ErrorResponseSerializer

from .serializers import FamilySubscriptionSerializer, ProviderSubscriptionSerializer

_PRIVATE_DETAILS_EXAMPLE = {
    "session_schedule": "Saturday mornings 9-11am",
    "exact_address": "Building 5, Al Waab Street, Doha",
    "materials_required": ["Sketch pad A3", "Charcoal pencils"],
}

_FAMILY_SUB_EXAMPLE = {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "listing_id": "550e8400-e29b-41d4-a716-446655440001",
    "provider_id": "12",
    "status": "CONFIRMED",
    "cancelled_at": None,
    "created_at": "2026-06-01T10:00:00Z",
    "updated_at": "2026-06-01T10:00:00Z",
    "listing_private_details": _PRIVATE_DETAILS_EXAMPLE,
}

_PROVIDER_SUB_EXAMPLE = {
    "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "listing_id": "550e8400-e29b-41d4-a716-446655440001",
    "listing_title": "Watercolour Masterclass — Pearl",
    "family": {"id": "user-uuid-here", "full_name": "Sara Al-Kuwari"},
    "status": "CONFIRMED",
    "cancelled_at": None,
    "created_at": "2026-06-01T10:00:00Z",
}

_FORBIDDEN_FAMILY = [
    OpenApiExample(
        "Not a family account",
        value={"detail": "You must be a family account to access this resource."},
        status_codes=["403"],
    )
]

_FORBIDDEN_PROVIDER = [
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

_STATUS_PARAM = OpenApiParameter(
    name="status",
    description="Filter by status (CONFIRMED, CANCELLED).",
    required=False,
    type=str,
)

_LISTING_ID_PARAM = OpenApiParameter(
    name="listing_id",
    description="Filter by listing UUID.",
    required=False,
    type=str,
)

# ---------------------------------------------------------------------------
# Family schemas
# ---------------------------------------------------------------------------

SUBSCRIPTION_LIST_SCHEMA = {
    "summary": "List own subscriptions",
    "description": (
        "Returns all subscriptions for the authenticated family, most recent first."
    ),
    "parameters": [_STATUS_PARAM],
    "responses": {
        200: OpenApiResponse(
            response=FamilySubscriptionSerializer(many=True),
            description="Paginated list of subscriptions.",
            examples=[
                OpenApiExample(
                    "List",
                    value={
                        "count": 1,
                        "next": None,
                        "previous": None,
                        "results": [_FAMILY_SUB_EXAMPLE],
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
            description="Not a family account.",
            examples=_FORBIDDEN_FAMILY,
        ),
    },
}

SUBSCRIPTION_CREATE_SCHEMA = {
    "summary": "Subscribe to a masterclass",
    "description": (
        "Subscribe to a MASTERCLASSES listing. Auto-confirms immediately.\n\n"
        "- Listing must be ACTIVE.\n"
        "- Listing category must be MASTERCLASSES.\n"
        "- Returns 409 if already CONFIRMED for this listing.\n"
        "- Response includes listing_private_details (schedule, address, materials)."
    ),
    "responses": {
        201: OpenApiResponse(
            response=FamilySubscriptionSerializer,
            description="Subscription created and confirmed.",
            examples=[
                OpenApiExample("Created", value=_FAMILY_SUB_EXAMPLE, status_codes=["201"])
            ],
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Listing not active or wrong category.",
            examples=[
                OpenApiExample(
                    "Wrong category",
                    value={
                        "detail": (
                            "Subscriptions only allowed on MASTERCLASSES listings; "
                            "use /inquiries/ for tutoring."
                        )
                    },
                    status_codes=["400"],
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
            description="Not a family account.",
            examples=_FORBIDDEN_FAMILY,
        ),
        409: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Already subscribed (CONFIRMED) to this listing.",
            examples=[
                OpenApiExample(
                    "Duplicate",
                    value={
                        "detail": (
                            "You already have an active subscription for this listing."
                        )
                    },
                    status_codes=["409"],
                )
            ],
        ),
    },
}

SUBSCRIPTION_RETRIEVE_SCHEMA = {
    "summary": "Retrieve own subscription",
    "description": "Returns detail including listing_private_details.",
    "responses": {
        200: OpenApiResponse(
            response=FamilySubscriptionSerializer,
            description="Subscription detail.",
            examples=[
                OpenApiExample("Detail", value=_FAMILY_SUB_EXAMPLE, status_codes=["200"])
            ],
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Authentication required.",
            examples=UNAUTHORIZED_EXAMPLES,
        ),
        403: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Not a family account.",
            examples=_FORBIDDEN_FAMILY,
        ),
        404: OpenApiResponse(description="Subscription not found."),
    },
}

SUBSCRIPTION_CANCEL_SCHEMA = {
    "summary": "Cancel subscription",
    "description": (
        "Soft-cancels the subscription (status → CANCELLED, cancelled_at set). "
        "The family may re-subscribe after cancellation."
    ),
    "responses": {
        204: OpenApiResponse(description="Subscription cancelled."),
        401: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Authentication required.",
            examples=UNAUTHORIZED_EXAMPLES,
        ),
        403: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Not a family account.",
            examples=_FORBIDDEN_FAMILY,
        ),
        404: OpenApiResponse(description="Subscription not found."),
    },
}

# ---------------------------------------------------------------------------
# Provider schemas
# ---------------------------------------------------------------------------

PROVIDER_SUBSCRIPTION_LIST_SCHEMA = {
    "summary": "List received subscriptions",
    "description": (
        "Returns subscriptions for masterclass listings owned by the provider. "
        "Filterable by ?status= and ?listing_id=."
    ),
    "parameters": [_STATUS_PARAM, _LISTING_ID_PARAM],
    "responses": {
        200: OpenApiResponse(
            response=ProviderSubscriptionSerializer(many=True),
            description="Paginated list of subscriptions.",
            examples=[
                OpenApiExample(
                    "List",
                    value={
                        "count": 1,
                        "next": None,
                        "previous": None,
                        "results": [_PROVIDER_SUB_EXAMPLE],
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
            description="Not a provider.",
            examples=_FORBIDDEN_PROVIDER,
        ),
    },
}

PROVIDER_SUBSCRIPTION_RETRIEVE_SCHEMA = {
    "summary": "Retrieve received subscription",
    "description": "Returns detail of a single subscription received by the provider.",
    "responses": {
        200: OpenApiResponse(
            response=ProviderSubscriptionSerializer,
            description="Subscription detail.",
            examples=[
                OpenApiExample(
                    "Detail", value=_PROVIDER_SUB_EXAMPLE, status_codes=["200"]
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
            description="Not a provider.",
            examples=_FORBIDDEN_PROVIDER,
        ),
        404: OpenApiResponse(description="Subscription not found."),
    },
}
