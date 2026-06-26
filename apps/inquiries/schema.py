"""
drf-spectacular OpenAPI schema helpers for the inquiries app.

Mirrors the pattern in apps/providers/schema.py and apps/users/schema.py.
"""

from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse

from apps.core.schema import UNAUTHORIZED_EXAMPLES, ErrorResponseSerializer

from apps.inquiries.serializers import FamilyInquirySerializer, TutorInquirySerializer

# ---------------------------------------------------------------------------
# Reusable example values
# ---------------------------------------------------------------------------

_TUTOR_BLOCK_EXAMPLE = {
    "id": 42,
    "full_name": "Sara Al-Thani",
    "subjects": ["MATH", "PHYSICS"],
    "is_verified": True,
}

_FAMILY_INQUIRY_EXAMPLE = {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "tutor_id": 42,
    "tutor": _TUTOR_BLOCK_EXAMPLE,
    "status": "NEW",
    "message": "I am interested in IGCSE maths tutoring for my daughter.",
    "contact_revealed": False,
    "created_at": "2026-06-01T10:00:00Z",
    "updated_at": "2026-06-01T10:00:00Z",
}

_TUTOR_INQUIRY_EXAMPLE = {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "tutor_id": 42,
    "family": {
        "id": "user-uuid-here",
        "full_name": None,
        "phone": None,
        "email": None,
    },
    "status": "NEW",
    "message": "I am interested in IGCSE maths tutoring for my daughter.",
    "contact_revealed": False,
    "created_at": "2026-06-01T10:00:00Z",
    "updated_at": "2026-06-01T10:00:00Z",
}

_FORBIDDEN_FAMILY = [
    OpenApiExample(
        "Not a family account",
        value={"detail": "You must be a family account to access this resource."},
        status_codes=["403"],
    )
]

_FORBIDDEN_TUTOR = [
    OpenApiExample(
        "Not a tutor",
        value={"detail": "Only users with the TUTOR role can access this resource."},
        status_codes=["403"],
    )
]

_CANCEL_CONFLICT_EXAMPLE = [
    OpenApiExample(
        "Already terminal",
        value={
            "detail": (
                "Cannot transition inquiry from 'COMPLETED' to 'CANCELLED'. "
                "Allowed next statuses: none (terminal state)."
            )
        },
        status_codes=["409"],
    ),
]

_STATUS_CONFLICT_EXAMPLE = [
    OpenApiExample(
        "Invalid transition",
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
        "Filter by inquiry status "
        "(NEW, CONTACTED, ACCEPTED, DECLINED, COMPLETED, CANCELLED)."
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
    "summary": "Submit an inquiry to a tutor",
    "description": (
        "Submit a new inquiry addressed to a tutor. Requires FAMILY role.\n\n"
        "- `tutor_id` is the TutorDetail id of the addressed tutor.\n"
        "- The tutor must not be soft-deleted.\n"
        "- Multiple inquiries to the same tutor are permitted"
        " (no duplicate prevention).\n"
        "- Status defaults to NEW."
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
            description="Validation error — tutor unavailable or bad input.",
            examples=[
                OpenApiExample(
                    "Tutor unavailable",
                    value={"detail": "This tutor is no longer available."},
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
        404: OpenApiResponse(description="Tutor not found."),
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

INQUIRY_CANCEL_SCHEMA = {
    "summary": "Cancel own inquiry",
    "description": (
        "Cancels an inquiry owned by the authenticated family. "
        "Transition: NEW|CONTACTED → CANCELLED. "
        "Returns 409 if the inquiry is already in a terminal state."
    ),
    "request": None,
    "responses": {
        200: OpenApiResponse(
            response=FamilyInquirySerializer,
            description="Inquiry after cancellation.",
            examples=[
                OpenApiExample(
                    "Cancelled",
                    value={**_FAMILY_INQUIRY_EXAMPLE, "status": "CANCELLED"},
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
        404: OpenApiResponse(
            description="Inquiry not found or not owned by this family."
        ),
        409: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Inquiry cannot be cancelled from its current status.",
            examples=_CANCEL_CONFLICT_EXAMPLE,
        ),
    },
}

# ---------------------------------------------------------------------------
# Tutor endpoint schemas
# ---------------------------------------------------------------------------

TUTOR_INQUIRY_LIST_SCHEMA = {
    "summary": "List received inquiries",
    "description": (
        "Returns all inquiries addressed to the authenticated tutor. "
        "Filter by ?status=. Requires TUTOR role."
    ),
    "parameters": [_STATUS_PARAM],
    "responses": {
        200: OpenApiResponse(
            response=TutorInquirySerializer(many=True),
            description="Paginated list of received inquiries.",
            examples=[
                OpenApiExample(
                    "List",
                    value={
                        "count": 1,
                        "next": None,
                        "previous": None,
                        "results": [_TUTOR_INQUIRY_EXAMPLE],
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
            description="Not a tutor.",
            examples=_FORBIDDEN_TUTOR,
        ),
    },
}

TUTOR_INQUIRY_RETRIEVE_SCHEMA = {
    "summary": "Retrieve received inquiry",
    "description": (
        "Returns detail of a single inquiry addressed to the authenticated tutor."
    ),
    "responses": {
        200: OpenApiResponse(
            response=TutorInquirySerializer,
            description="Inquiry detail with redacted family contact block.",
            examples=[
                OpenApiExample(
                    "Detail", value=_TUTOR_INQUIRY_EXAMPLE, status_codes=["200"]
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
            description="Not a tutor.",
            examples=_FORBIDDEN_TUTOR,
        ),
        404: OpenApiResponse(
            description="Inquiry not found or not addressed to this tutor."
        ),
    },
}

TUTOR_INQUIRY_UPDATE_SCHEMA = {
    "summary": "Update inquiry status",
    "description": (
        "Update the status of an inquiry addressed to the authenticated tutor.\n\n"
        "Body: `{\"status\": \"<TARGET>\"}` where TARGET is one of "
        "CONTACTED, ACCEPTED, DECLINED, COMPLETED.\n\n"
        "Allowed transitions:\n"
        "- NEW → CONTACTED, ACCEPTED, DECLINED\n"
        "- CONTACTED → ACCEPTED, DECLINED\n"
        "- ACCEPTED → COMPLETED\n\n"
        "Returns 409 if the transition is not allowed from the current status."
    ),
    "responses": {
        200: OpenApiResponse(
            response=TutorInquirySerializer,
            description="Inquiry after the status update.",
            examples=[
                OpenApiExample(
                    "Accepted",
                    value={
                        **_TUTOR_INQUIRY_EXAMPLE,
                        "status": "ACCEPTED",
                        "contact_revealed": True,
                    },
                    status_codes=["200"],
                )
            ],
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Invalid status value in request body.",
        ),
        401: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Authentication required.",
            examples=UNAUTHORIZED_EXAMPLES,
        ),
        403: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Not a tutor.",
            examples=_FORBIDDEN_TUTOR,
        ),
        404: OpenApiResponse(description="Inquiry not found."),
        409: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Invalid state transition.",
            examples=_STATUS_CONFLICT_EXAMPLE,
        ),
    },
}
