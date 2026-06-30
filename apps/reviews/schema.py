"""
drf-spectacular schema hints for the reviews endpoints — Phase 7.
"""

from drf_spectacular.utils import OpenApiParameter, OpenApiTypes

LISTING_REVIEWS_LIST_SCHEMA = {
    "summary": "List reviews for a listing",
    "description": (
        "Returns paginated reviews for the given listing, most recent first. "
        "No authentication required."
    ),
    "parameters": [
        OpenApiParameter(
            "listing_id",
            OpenApiTypes.UUID,
            OpenApiParameter.PATH,
            description="UUID of the listing.",
        )
    ],
}

LISTING_REVIEWS_CREATE_SCHEMA = {
    "summary": "Post a review on a listing",
    "description": (
        "Create a review for the given listing. "
        "Requires authentication with role=FAMILY. "
        "For TUTORING listings, the family must have an ACCEPTED or COMPLETED inquiry. "
        "For MASTERCLASSES listings, the family must have at least one subscription. "
        "Returns 400 if the engagement gate fails, 409 if a review already exists."
    ),
}

MY_REVIEWS_LIST_SCHEMA = {
    "summary": "List own reviews",
    "description": "Returns all reviews written by the authenticated family user.",
}

TUTOR_REVIEWS_LIST_SCHEMA = {
    "summary": "List reviews for a tutor",
    "description": (
        "Returns paginated reviews for the given tutor, most recent first. "
        "No authentication required."
    ),
    "parameters": [
        OpenApiParameter(
            "tutor_id",
            OpenApiTypes.INT,
            OpenApiParameter.PATH,
            description="ID of the tutor (TutorDetail).",
        )
    ],
}

TUTOR_REVIEWS_CREATE_SCHEMA = {
    "summary": "Post a review on a tutor",
    "description": (
        "Create a review for the given tutor. "
        "Requires authentication with role=FAMILY. "
        "The family must have an Inquiry with this tutor in "
        "CONTACTED, ACCEPTED, or COMPLETED. "
        "Returns 400 if the engagement gate fails, 409 if a review already exists."
    ),
}

TUTOR_REVIEW_BY_AUTHOR_SCHEMA = {
    "summary": "Get a single tutor review by tutor and author",
    "description": (
        "Returns the review written by the given author for the given tutor, "
        "or 404 if none exists. No authentication required. Useful for deciding "
        "whether to show an edit or create flow."
    ),
    "parameters": [
        OpenApiParameter(
            "tutor_id",
            OpenApiTypes.INT,
            OpenApiParameter.PATH,
            description="ID of the tutor (TutorDetail).",
        ),
        OpenApiParameter(
            "author_id",
            OpenApiTypes.INT,
            OpenApiParameter.PATH,
            description="ID of the review author (user).",
        ),
    ],
}

TUTOR_REVIEW_DETAIL_SCHEMA = {
    "summary": "Update or delete own tutor review",
    "description": (
        "PATCH: update rating/text of an existing tutor review. "
        "DELETE: remove the review. "
        "Both actions trigger a rating recompute on the tutor. "
        "Returns 404 if the review does not belong to the authenticated user."
    ),
}

REVIEW_DETAIL_SCHEMA = {
    "summary": "Update or delete own review",
    "description": (
        "PATCH: update rating/text of an existing review. "
        "DELETE: remove the review. "
        "Both actions trigger a rating recompute on the parent listing."
    ),
}
