from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema


FAVORITE_LIST_SCHEMA = extend_schema(
    tags=["favorites"],
    summary="List my favorites",
    description="Returns the authenticated user's saved listings.",
)

FAVORITE_CREATE_SCHEMA = extend_schema(
    tags=["favorites"],
    summary="Create a favorite",
    description="Saves a listing to the authenticated user's favorites.",
)

FAVORITE_RETRIEVE_SCHEMA = extend_schema(
    tags=["favorites"],
    summary="Get a favorite",
    description=(
        "Returns the authenticated user's favorite record for the given "
        "listing UUID."
    ),
    parameters=[
        OpenApiParameter(
            "listing_id",
            OpenApiTypes.UUID,
            OpenApiParameter.PATH,
            description="UUID of the listing saved by the authenticated user.",
        )
    ],
)

FAVORITE_DELETE_SCHEMA = extend_schema(
    tags=["favorites"],
    summary="Delete a favorite",
    description=(
        "Removes the authenticated user's saved favorite for the given "
        "listing UUID."
    ),
    parameters=[
        OpenApiParameter(
            "listing_id",
            OpenApiTypes.UUID,
            OpenApiParameter.PATH,
            description="UUID of the listing to remove from favorites.",
        )
    ],
)
