"""
drf-spectacular OpenAPI schema helpers for the inquiries app.

Mirrors the pattern in apps/providers/schema.py and apps/users/schema.py.
"""

from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse

from apps.core.schema import UNAUTHORIZED_EXAMPLES, ErrorResponseSerializer

from .serializers import FamilyInquirySerializer, ProviderInquirySerializer

# ---------------------------------------------------------------------------
# Reusable example values
# ---------------------------------------------------------------------------

_FAMILY_INQUIRY_EXAMPLE = {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "listing_id": "550e8400-e29b-41d4-a716-446655440000",
    "provider_id": "7",
    "status": "NEW",
    "message": "I am interested in IGCSE maths tutoring for my daughter.",
    "contact_revealed": False,
    "created_at": "2026-06-01T10:00:00Z",
    "updated_at": "2026-06-01T10:00:00Z",
}

_PROVIDER_INQUIRY_EXAMPLE = {
    **_FAMILY_INQUIRY_EXAMPLE,
    "family": {
        "id": "user-uuid-here",
        "full_name": None,
        "phone": None,
        "email": None,
    },
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

_CONFLICT_EXAMPLE = [
    OpenApiExample(
        "Invalid transition",
        value={
            "detail": (
                "Cannot transition inquiry from 'DECLINED' to 'COMPLETED'. "
                "Allowed next statuses: none (terminal state)."
            )
        },
        status_codes=["409"],
    ),
    OpenApiExample(
        "Invalid transition — accepted to contacted",
        value={
            "detail": (
                "Cannot transition inquiry from 'ACCEPTED' to 'CONTACTED'. "
                "Allowed next statuses: ['COMPLETED']."
            )
        },
        status_codes=["409"],
    ),
]

_STATUS_PARAM = OpenApiParameter(
    name="status",
    description=(
        "Filter by inquiry status (NEW, CONTACTED, ACCEPTED, DECLINED, COMPLETED)."
    ),
    required=False,
    type=str,
)

# ---------------------------------------------------------------------------
# Family endpoint schemas
# ---------------------------------------------------------------------------

INQUIRY_LIST_SCHEMA = {
    "summary": "List own inquiries",
    "description": (
        "Returns all inquiries submitted by the authenticated family, "
        "ordered most-recent first. Requires FAMILY role."
    ),
    "parameters": [_STATUS_PARAM],
    "responses": {
        200: OpenApiResponse(
            response=FamilyInquirySerializer(many=True),
            description="Paginated list of own inquiries.",
            examples=[
                OpenApiExample(
                    "List",
                    value={
                        "count": 1,
                        "next": None,
                        "previous": None,
                        "results": [_FAMILY_INQUIRY_EXAMPLE],
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

INQUIRY_CREATE_SCHEMA = {
    "summary": "Submit an inquiry",
    "description": (
        "Submit a new inquiry on a TUTORING listing. Requires FAMILY role.\n\n"
        "- Listing must be ACTIVE.\n"
        "- Listing category must be TUTORING (use /subscriptions/ for MASTERCLASSES).\n"
        "- Multiple inquiries on the same listing are permitted"
        " (no duplicate prevention).\n"
        "- Status defaults to NEW; provider is snapshotted from listing.owner."
    ),
    "responses": {
        201: OpenApiResponse(
            response=FamilyInquirySerializer,
            description="Inquiry created.",
            examples=[
                OpenApiExample(
                    "Created",
                    value=_FAMILY_INQUIRY_EXAMPLE,
                    status_codes=["201"],
                )
            ],
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer,
            description=(
                "Validation error — listing not found, not active, or wrong category."
            ),
            examples=[
                OpenApiExample(
                    "Wrong category",
                    value={
                        "detail": (
                            "Inquiries only allowed on TUTORING listings; "
                            "use /subscriptions/ for masterclasses."
                        )
                    },
                    status_codes=["400"],
                ),
                OpenApiExample(
                    "Listing not active",
                    value={"detail": "Listing is not active."},
                    status_codes=["400"],
                ),
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

INQUIRY_RETRIEVE_SCHEMA = {
    "summary": "Retrieve own inquiry",
    "description": (
        "Returns detail of a single inquiry owned by the authenticated family."
    ),
    "responses": {
        200: OpenApiResponse(
            response=FamilyInquirySerializer,
            description="Inquiry detail.",
            examples=[
                OpenApiExample(
                    "Detail", value=_FAMILY_INQUIRY_EXAMPLE, status_codes=["200"]
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
        404: OpenApiResponse(
            description="Inquiry not found or not owned by this family."
        ),
    },
}

# ---------------------------------------------------------------------------
# Provider endpoint schemas
# ---------------------------------------------------------------------------

PROVIDER_INQUIRY_LIST_SCHEMA = {
    "summary": "List received inquiries",
    "description": (
        "Returns all inquiries where the authenticated provider is the recipient. "
        "Filter by ?status=. MASTERCLASS providers will see an empty list "
        "(their flow uses subscriptions, not inquiries)."
    ),
    "parameters": [_STATUS_PARAM],
    "responses": {
        200: OpenApiResponse(
            response=ProviderInquirySerializer(many=True),
            description="Paginated list of received inquiries.",
            examples=[
                OpenApiExample(
                    "List",
                    value={
                        "count": 1,
                        "next": None,
                        "previous": None,
                        "results": [_PROVIDER_INQUIRY_EXAMPLE],
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

PROVIDER_INQUIRY_RETRIEVE_SCHEMA = {
    "summary": "Retrieve received inquiry",
    "description": (
        "Returns detail of a single inquiry received by the authenticated provider."
    ),
    "responses": {
        200: OpenApiResponse(
            response=ProviderInquirySerializer,
            description="Inquiry detail with redacted family contact block.",
            examples=[
                OpenApiExample(
                    "Detail", value=_PROVIDER_INQUIRY_EXAMPLE, status_codes=["200"]
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
        404: OpenApiResponse(
            description="Inquiry not found or not received by this provider."
        ),
    },
}

_TRANSITION_RESPONSES = {
    200: OpenApiResponse(
        response=ProviderInquirySerializer,
        description="Inquiry after transition.",
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
    404: OpenApiResponse(description="Inquiry not found."),
    409: OpenApiResponse(
        response=ErrorResponseSerializer,
        description="Invalid state transition.",
        examples=_CONFLICT_EXAMPLE,
    ),
}

PROVIDER_INQUIRY_CONTACTED_SCHEMA = {
    "summary": "Mark inquiry as Contacted",
    "description": "Transition: NEW → CONTACTED. Returns 409 if not in NEW status.",
    "responses": _TRANSITION_RESPONSES,
}

PROVIDER_INQUIRY_ACCEPT_SCHEMA = {
    "summary": "Accept inquiry",
    "description": "Transition: NEW|CONTACTED → ACCEPTED. Returns 409 if invalid status.",
    "responses": _TRANSITION_RESPONSES,
}

PROVIDER_INQUIRY_DECLINE_SCHEMA = {
    "summary": "Decline inquiry",
    "description": "Transition: NEW|CONTACTED → DECLINED. Returns 409 if invalid status.",
    "responses": _TRANSITION_RESPONSES,
}

PROVIDER_INQUIRY_COMPLETE_SCHEMA = {
    "summary": "Complete inquiry",
    "description": "Transition: ACCEPTED → COMPLETED. Returns 409 if not ACCEPTED.",
    "responses": _TRANSITION_RESPONSES,
}
