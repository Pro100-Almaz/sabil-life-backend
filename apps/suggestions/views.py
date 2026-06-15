"""
Suggestion views — Phase 5.

Family endpoints only:
  GET/POST /api/v1/suggestions/       — list own / create
  GET      /api/v1/suggestions/{id}/  — detail

Admin management is via Django admin panel only — no REST admin endpoints.
"""

import logging

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response

from .models import ServiceSuggestion
from .permissions import IsFamily
from .schema import (
    SUGGESTION_CREATE_SCHEMA,
    SUGGESTION_LIST_SCHEMA,
    SUGGESTION_RETRIEVE_SCHEMA,
)
from .serializers import SuggestionCreateSerializer, SuggestionSerializer

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(**SUGGESTION_LIST_SCHEMA),
    create=extend_schema(**SUGGESTION_CREATE_SCHEMA),
    retrieve=extend_schema(**SUGGESTION_RETRIEVE_SCHEMA),
)
class FamilySuggestionViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Family-side suggestion endpoints.

    list     — GET  /api/v1/suggestions/       — own suggestions, most recent first.
    create   — POST /api/v1/suggestions/       — submit a new service suggestion.
    retrieve — GET  /api/v1/suggestions/{id}/  — detail of own suggestion.

    Only FAMILY role users may access these endpoints.
    admin_notes is never included in any response — admin-only field.
    """

    permission_classes = [permissions.IsAuthenticated, IsFamily]
    lookup_field = "id"

    def get_queryset(self):
        return ServiceSuggestion.objects.filter(family=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return SuggestionCreateSerializer
        return SuggestionSerializer

    def create(self, request, *args, **kwargs):
        serializer = SuggestionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        suggestion = serializer.save(family=request.user)
        logger.info(
            "Family %s submitted suggestion %s.",
            request.user.email,
            suggestion.id,
        )
        out_serializer = SuggestionSerializer(suggestion, context={"request": request})
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)
