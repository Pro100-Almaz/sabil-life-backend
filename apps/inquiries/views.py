"""
Inquiry views — Phase 5.

Family endpoints:
  GET/POST /api/v1/inquiries/        — list own / create
  GET      /api/v1/inquiries/{id}/   — detail

Provider endpoints:
  GET  /api/v1/provider/inquiries/              — list received (filter ?status=)
  GET  /api/v1/provider/inquiries/{id}/         — detail
  POST /api/v1/provider/inquiries/{id}/contacted/ — NEW → CONTACTED
  POST /api/v1/provider/inquiries/{id}/accept/    — NEW|CONTACTED → ACCEPTED
  POST /api/v1/provider/inquiries/{id}/decline/   — NEW|CONTACTED → DECLINED
  POST /api/v1/provider/inquiries/{id}/complete/  — ACCEPTED → COMPLETED
"""

import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.catalog.models import Listing
from apps.users.permissions import IsProvider

from apps.inquiries import services
from apps.inquiries.models import Inquiry, InquiryStatus
from apps.inquiries.permissions import IsFamily
from apps.inquiries.schema import (
    INQUIRY_CREATE_SCHEMA,
    INQUIRY_LIST_SCHEMA,
    INQUIRY_RETRIEVE_SCHEMA,
    PROVIDER_INQUIRY_ACCEPT_SCHEMA,
    PROVIDER_INQUIRY_COMPLETE_SCHEMA,
    PROVIDER_INQUIRY_CONTACTED_SCHEMA,
    PROVIDER_INQUIRY_DECLINE_SCHEMA,
    PROVIDER_INQUIRY_LIST_SCHEMA,
    PROVIDER_INQUIRY_RETRIEVE_SCHEMA,
)
from apps.inquiries.serializers import (
    FamilyInquirySerializer,
    InquiryCreateSerializer,
    ProviderInquirySerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Family ViewSet
# ---------------------------------------------------------------------------


@extend_schema_view(
    list=extend_schema(**INQUIRY_LIST_SCHEMA),
    create=extend_schema(**INQUIRY_CREATE_SCHEMA),
    retrieve=extend_schema(**INQUIRY_RETRIEVE_SCHEMA),
)
class FamilyInquiryViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Family-side inquiry endpoints.

    list   — GET  /api/v1/inquiries/       — own inquiries, most recent first.
    create — POST /api/v1/inquiries/       — create new inquiry on TUTORING listing.
    retrieve — GET /api/v1/inquiries/{id}/ — detail of own inquiry.

    Only FAMILY role users may access these endpoints.
    """

    permission_classes = [permissions.IsAuthenticated, IsFamily]
    lookup_field = "id"

    def get_queryset(self):
        return Inquiry.objects.filter(family=self.request.user).select_related(
            "listing", "provider"
        )

    def get_serializer_class(self):
        if self.action == "create":
            return InquiryCreateSerializer
        return FamilyInquirySerializer

    def create(self, request, *args, **kwargs):
        input_serializer = InquiryCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        listing_id = input_serializer.validated_data["listing_id"]
        message = input_serializer.validated_data["message"]

        listing = get_object_or_404(Listing, pk=listing_id)

        try:
            inquiry = services.create_inquiry(
                family=request.user,
                listing=listing,
                message=message,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        out_serializer = FamilyInquirySerializer(inquiry, context={"request": request})
        logger.info(
            "Family %s created inquiry %s for listing %s.",
            request.user.email,
            inquiry.id,
            listing_id,
        )
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        inquiry = get_object_or_404(Inquiry, id=kwargs["id"], family=request.user)
        serializer = FamilyInquirySerializer(inquiry, context={"request": request})
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Provider ViewSet
# ---------------------------------------------------------------------------


@extend_schema_view(
    list=extend_schema(**PROVIDER_INQUIRY_LIST_SCHEMA),
    retrieve=extend_schema(**PROVIDER_INQUIRY_RETRIEVE_SCHEMA),
    contacted=extend_schema(**PROVIDER_INQUIRY_CONTACTED_SCHEMA),
    accept=extend_schema(**PROVIDER_INQUIRY_ACCEPT_SCHEMA),
    decline=extend_schema(**PROVIDER_INQUIRY_DECLINE_SCHEMA),
    complete=extend_schema(**PROVIDER_INQUIRY_COMPLETE_SCHEMA),
)
class ProviderInquiryViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Provider-side inquiry endpoints.

    Providers see inquiries where provider == request.user.
    Both TUTOR and MASTERCLASS providers can access the list (MASTERCLASS
    providers will simply see an empty list since their listings use subscriptions).

    Transition actions:
      contacted — NEW → CONTACTED
      accept    — NEW|CONTACTED → ACCEPTED
      decline   — NEW|CONTACTED → DECLINED
      complete  — ACCEPTED → COMPLETED
    """

    serializer_class = ProviderInquirySerializer
    permission_classes = [permissions.IsAuthenticated, IsProvider]
    lookup_field = "id"

    def get_queryset(self):
        qs = Inquiry.objects.filter(provider=self.request.user).select_related(
            "family", "listing"
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        return qs

    def retrieve(self, request, *args, **kwargs):
        inquiry = get_object_or_404(Inquiry, id=kwargs["id"], provider=request.user)
        serializer = ProviderInquirySerializer(inquiry, context={"request": request})
        return Response(serializer.data)

    def _do_transition(self, request, pk, target_status: str):
        inquiry = get_object_or_404(Inquiry, id=pk, provider=request.user)
        try:
            inquiry = services.transition(inquiry, target_status, actor=request.user)
        except services.InvalidTransition as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        serializer = ProviderInquirySerializer(inquiry, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="contacted")
    def contacted(self, request, id=None):
        return self._do_transition(request, id, InquiryStatus.CONTACTED)

    @action(detail=True, methods=["post"], url_path="accept")
    def accept(self, request, id=None):
        return self._do_transition(request, id, InquiryStatus.ACCEPTED)

    @action(detail=True, methods=["post"], url_path="decline")
    def decline(self, request, id=None):
        return self._do_transition(request, id, InquiryStatus.DECLINED)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, id=None):
        return self._do_transition(request, id, InquiryStatus.COMPLETED)
