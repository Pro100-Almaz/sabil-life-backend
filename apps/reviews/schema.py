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

REVIEW_DETAIL_SCHEMA = {
    "summary": "Update or delete own review",
    "description": (
        "PATCH: update rating/text of an existing review. "
        "DELETE: remove the review. "
        "Both actions trigger a rating recompute on the parent listing."
    ),
}
