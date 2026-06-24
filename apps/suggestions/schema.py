"""
drf-spectacular OpenAPI schema helpers for the suggestions app.
"""

from drf_spectacular.utils import OpenApiExample, OpenApiResponse

from apps.core.schema import UNAUTHORIZED_EXAMPLES, ErrorResponseSerializer

from apps.suggestions.serializers import SuggestionSerializer

_SUGGESTION_EXAMPLE = {
    "id": 1,
    "category": "MASTERCLASSES",
    "neighborhood": "Lusail",
    "message": "Kids pottery class please — nothing available in Lusail.",
    "status": "NEW",
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

SUGGESTION_LIST_SCHEMA = {
    "summary": "List own suggestions",
    "description": (
        "Returns all service suggestions submitted by the authenticated family, "
        "most recent first. admin_notes is never included in the response."
    ),
    "responses": {
        200: OpenApiResponse(
            response=SuggestionSerializer(many=True),
            description="Paginated list of suggestions.",
            examples=[
                OpenApiExample(
                    "List",
                    value={
                        "count": 1,
                        "next": None,
                        "previous": None,
                        "results": [_SUGGESTION_EXAMPLE],
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

SUGGESTION_CREATE_SCHEMA = {
    "summary": "Submit a service suggestion",
    "description": (
        "Submit a suggestion for a new service. Requires FAMILY role.\n\n"
        "`message` is required. `category` and `neighborhood` are optional hints "
        "to help the admin source the right service.\n\n"
        "Only FAMILY users may submit suggestions. "
        "Providers use the listing creation flow to offer services."
    ),
    "responses": {
        201: OpenApiResponse(
            response=SuggestionSerializer,
            description="Suggestion submitted.",
            examples=[
                OpenApiExample("Created", value=_SUGGESTION_EXAMPLE, status_codes=["201"])
            ],
        ),
        400: OpenApiResponse(
            response=ErrorResponseSerializer,
            description="Validation error — message is required.",
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

SUGGESTION_RETRIEVE_SCHEMA = {
    "summary": "Retrieve own suggestion",
    "description": (
        "Returns detail of a single suggestion submitted by the authenticated family."
    ),
    "responses": {
        200: OpenApiResponse(
            response=SuggestionSerializer,
            description="Suggestion detail.",
            examples=[
                OpenApiExample("Detail", value=_SUGGESTION_EXAMPLE, status_codes=["200"])
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
        404: OpenApiResponse(description="Suggestion not found."),
    },
}
