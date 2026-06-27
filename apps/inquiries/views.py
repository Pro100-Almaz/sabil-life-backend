"""
Inquiry views.

Family endpoints (FAMILY role):
  GET  /api/v1/inquiries/             — list own inquiries (filter ?status=)
  POST /api/v1/inquiries/             — create new inquiry addressed to a tutor
  GET  /api/v1/inquiries/{id}/        — detail of own inquiry
  POST /api/v1/inquiries/{id}/cancel/ — cancel own inquiry (→ CANCELLED)

Tutor endpoints (TUTOR role):
  GET   /api/v1/tutor/inquiries/      — list received inquiries (filter ?status=)
  GET   /api/v1/tutor/inquiries/{id}/ — detail of received inquiry
  PATCH /api/v1/tutor/inquiries/{id}/ — update status (CONTACTED/ACCEPTED/...)

MASTERCLASS / ADMIN / MANAGER have no inquiry endpoints.
"""

import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.providers.models import TutorDetail
from apps.users.permissions import IsTutor

from apps.inquiries import services
from apps.inquiries.models import Inquiry, InquiryStatus
from apps.inquiries.permissions import IsFamily
from apps.inquiries.schema import (
    INQUIRY_CANCEL_SCHEMA,
    INQUIRY_CREATE_SCHEMA,
    INQUIRY_LIST_SCHEMA,
    INQUIRY_RETRIEVE_SCHEMA,
    TUTOR_INQUIRY_LIST_SCHEMA,
    TUTOR_INQUIRY_RETRIEVE_SCHEMA,
    TUTOR_INQUIRY_UPDATE_SCHEMA,
)
from apps.inquiries.serializers import (
    FamilyInquirySerializer,
    InquiryCreateSerializer,
    InquiryStatusUpdateSerializer,
    TutorInquirySerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Family ViewSet
# ---------------------------------------------------------------------------


@extend_schema_view(
    list=extend_schema(**INQUIRY_LIST_SCHEMA),
    create=extend_schema(**INQUIRY_CREATE_SCHEMA),
    retrieve=extend_schema(**INQUIRY_RETRIEVE_SCHEMA),
    cancel=extend_schema(**INQUIRY_CANCEL_SCHEMA),
)
class FamilyInquiryViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Family-side inquiry endpoints.

    list     — GET  /api/v1/inquiries/             — own inquiries, recent first.
    create   — POST /api/v1/inquiries/             — new inquiry addressed to a tutor.
    retrieve — GET  /api/v1/inquiries/{id}/        — detail of own inquiry.
    cancel   — POST /api/v1/inquiries/{id}/cancel/ — cancel own inquiry.

    Only FAMILY role users may access these endpoints.
    """

    permission_classes = [permissions.IsAuthenticated, IsFamily]
    lookup_field = "id"

    def get_queryset(self):
        qs = Inquiry.objects.filter(family=self.request.user).select_related(
            "tutor", "tutor__user"
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return InquiryCreateSerializer
        return FamilyInquirySerializer

    def create(self, request, *args, **kwargs):
        input_serializer = InquiryCreateSerializer(
            data=request.data, context={"request": request}
        )
        input_serializer.is_valid(raise_exception=True)

        tutor_id = input_serializer.validated_data["tutor_id"]
        message = input_serializer.validated_data["message"]

        tutor = get_object_or_404(TutorDetail, id=tutor_id)

        try:
            inquiry = services.create_inquiry(
                family=request.user,
                tutor=tutor,
                message=message,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        out_serializer = FamilyInquirySerializer(inquiry, context={"request": request})
        logger.info(
            "Family %s created inquiry %s for tutor %s.",
            request.user.email,
            inquiry.id,
            tutor_id,
        )
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        inquiry = get_object_or_404(
            self.get_queryset(), id=kwargs["id"]
        )
        serializer = FamilyInquirySerializer(inquiry, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, id=None):
        inquiry = get_object_or_404(self.get_queryset(), id=id)
        try:
            inquiry = services.transition(
                inquiry, InquiryStatus.CANCELLED, actor=request.user
            )
        except services.InvalidTransition as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        serializer = FamilyInquirySerializer(inquiry, context={"request": request})
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Tutor ViewSet
# ---------------------------------------------------------------------------


@extend_schema_view(
    list=extend_schema(**TUTOR_INQUIRY_LIST_SCHEMA),
    retrieve=extend_schema(**TUTOR_INQUIRY_RETRIEVE_SCHEMA),
    partial_update=extend_schema(**TUTOR_INQUIRY_UPDATE_SCHEMA),
)
class TutorInquiryViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Tutor-side inquiry endpoints.

    Tutors see inquiries addressed to their TutorDetail profile.

    list           — GET   /api/v1/tutor/inquiries/      (filter ?status=)
    retrieve       — GET   /api/v1/tutor/inquiries/{id}/
    partial_update — PATCH /api/v1/tutor/inquiries/{id}/  body: {"status": "..."}

    Allowed status transitions (validated by the state machine):
      CONTACTED — NEW → CONTACTED
      ACCEPTED  — NEW|CONTACTED → ACCEPTED
      DECLINED  — NEW|CONTACTED → DECLINED
      COMPLETED — ACCEPTED → COMPLETED
    """

    serializer_class = TutorInquirySerializer
    permission_classes = [permissions.IsAuthenticated, IsTutor]
    lookup_field = "id"
    # PATCH only — no PUT/POST/DELETE on tutor inquiries.
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        qs = Inquiry.objects.filter(tutor__user=self.request.user).select_related(
            "family", "tutor", "tutor__user"
        )
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        return qs

    def retrieve(self, request, *args, **kwargs):
        inquiry = get_object_or_404(self.get_queryset(), id=kwargs["id"])
        serializer = TutorInquirySerializer(inquiry, context={"request": request})
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        inquiry = get_object_or_404(self.get_queryset(), id=kwargs["id"])

        input_serializer = InquiryStatusUpdateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        target_status = input_serializer.validated_data["status"]

        try:
            inquiry = services.transition(inquiry, target_status, actor=request.user)
        except services.InvalidTransition as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        logger.info(
            "Tutor %s moved inquiry %s to %s.",
            request.user.email,
            inquiry.id,
            target_status,
        )
        serializer = TutorInquirySerializer(inquiry, context={"request": request})
        return Response(serializer.data)
