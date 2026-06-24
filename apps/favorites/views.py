from drf_spectacular.utils import extend_schema_view
from rest_framework import permissions, viewsets

from .models import Favorite
from .schema import (
    FAVORITE_CREATE_SCHEMA,
    FAVORITE_DELETE_SCHEMA,
    FAVORITE_LIST_SCHEMA,
    FAVORITE_RETRIEVE_SCHEMA,
)
from .serializers import FavoriteSerializer


@extend_schema_view(
    list=FAVORITE_LIST_SCHEMA,
    create=FAVORITE_CREATE_SCHEMA,
    retrieve=FAVORITE_RETRIEVE_SCHEMA,
    destroy=FAVORITE_DELETE_SCHEMA,
)
class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete"]
    lookup_field = "listing_id"
    lookup_url_kwarg = "listing_id"
    lookup_value_regex = (
        "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        "[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    )

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related(
            "listing",
            "user",
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
