import logging

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, mixins, permissions, viewsets
import rest_framework.exceptions
import rest_framework.parsers
import rest_framework.status
from rest_framework.response import Response

from apps.catalog.models import Listing, ListingStatus

from .models import ProviderProfile, TutorDetail
from .permissions import IsListingOwner, IsProvider, IsTutor
from .schema import (
    PROVIDER_LISTING_CREATE_SCHEMA,
    PROVIDER_LISTING_DESTROY_SCHEMA,
    PROVIDER_LISTING_LIST_SCHEMA,
    PROVIDER_LISTING_RETRIEVE_SCHEMA,
    PROVIDER_LISTING_UPDATE_SCHEMA,
    PROVIDER_PROFILE_GET_SCHEMA,
    PROVIDER_PROFILE_PATCH_SCHEMA,
)
from .serializers import (
    AvatarUploadSerializer,
    ProviderListingSerializer,
    ProviderProfileSerializer,
    TutorDetailSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@extend_schema_view(
    get=extend_schema(**PROVIDER_PROFILE_GET_SCHEMA),
    patch=extend_schema(**PROVIDER_PROFILE_PATCH_SCHEMA),
)
class ProviderProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/v1/provider/profile/  — retrieve own profile (lazy-create on first access).
    PATCH /api/v1/provider/profile/ — update writable profile fields.

    PUT is disabled; only PATCH is accepted.

    Auth: IsAuthenticated + IsProvider (TUTOR or MASTERCLASS only).
    is_verified is read-only — only admins flip it on the User model.
    """

    serializer_class = ProviderProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsProvider]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self) -> ProviderProfile:
        profile = ProviderProfile.objects.get_or_create_for_user(self.request.user)
        self.check_object_permissions(self.request, profile)
        return profile


# ---------------------------------------------------------------------------
# Tutor Detail
# ---------------------------------------------------------------------------


class TutorDetailView(generics.CreateAPIView, generics.RetrieveUpdateAPIView):
    """
    GET   /api/v1/provider/tutor-detail/ — retrieve own tutor detail.
    POST  /api/v1/provider/tutor-detail/ — create tutor detail.
    PATCH /api/v1/provider/tutor-detail/ — update tutor detail.

    Auth: IsAuthenticated + IsTutor.
    Avatar is uploaded as a file (multipart/form-data).
    """

    serializer_class = TutorDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsTutor]
    http_method_names = ["get", "post", "patch", "head", "options"]
    parser_classes = [
        rest_framework.parsers.MultiPartParser,
        rest_framework.parsers.FormParser,
        rest_framework.parsers.JSONParser,
    ]

    def get_object(self) -> TutorDetail:
        try:
            obj = TutorDetail.objects.get(user=self.request.user)
        except TutorDetail.DoesNotExist:
            raise rest_framework.exceptions.NotFound("Tutor detail not found.")
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_create(self, serializer) -> None:
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        if TutorDetail.objects.filter(user=request.user).exists():
            return Response(
                {"detail": "Tutor detail already exists. Use PATCH to update."},
                status=rest_framework.status.HTTP_409_CONFLICT,
            )
        return super().create(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Avatar Upload
# ---------------------------------------------------------------------------


class AvatarUploadView(generics.UpdateAPIView):
    """
    POST /api/v1/provider/avatar/ — upload/replace tutor avatar.

    Returns {"avatar_url": "<full URL>"}.
    """

    serializer_class = AvatarUploadSerializer
    permission_classes = [permissions.IsAuthenticated, IsTutor]
    http_method_names = ["post", "options"]
    parser_classes = [
        rest_framework.parsers.MultiPartParser,
        rest_framework.parsers.FormParser,
    ]

    def get_object(self) -> TutorDetail:
        obj, _ = TutorDetail.objects.get_or_create(user=self.request.user)
        return obj

    def post(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Provider-owned Listings
# ---------------------------------------------------------------------------


@extend_schema_view(
    list=extend_schema(**PROVIDER_LISTING_LIST_SCHEMA),
    create=extend_schema(**PROVIDER_LISTING_CREATE_SCHEMA),
    retrieve=extend_schema(**PROVIDER_LISTING_RETRIEVE_SCHEMA),
    partial_update=extend_schema(**PROVIDER_LISTING_UPDATE_SCHEMA),
    destroy=extend_schema(**PROVIDER_LISTING_DESTROY_SCHEMA),
)
class ProviderListingViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    CRUD viewset for listings owned by the authenticated provider.

    GET    /api/v1/provider/listings/        — list own listings (all statuses)
    POST   /api/v1/provider/listings/        — create new listing
    GET    /api/v1/provider/listings/{id}/   — retrieve own listing
    PATCH  /api/v1/provider/listings/{id}/   — update own listing
    DELETE /api/v1/provider/listings/{id}/   — hard-delete own listing

    PUT is not wired in the router — PATCH only.

    Queryset is always filtered to owner=request.user, so cross-provider
    access returns 404, not 403 (information hiding).

    Status rule (enforced in perform_create / perform_update):
        is_verified=True  → PENDING  (submitted for admin approval)
        is_verified=False → DRAFT    (provider can edit; cannot publish yet)
    Provider cannot set status directly — the field is read_only in the
    serializer and forced server-side on every write.

    Owner is auto-assigned on create; any owner field in the request body
    is ignored (owner is read_only in the serializer).
    """

    serializer_class = ProviderListingSerializer
    permission_classes = [permissions.IsAuthenticated, IsProvider]
    lookup_field = "id"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Listing.objects.filter(owner=self.request.user)

    def get_permissions(self):
        if self.action in {"retrieve", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                IsProvider(),
                IsListingOwner(),
            ]
        return [permissions.IsAuthenticated(), IsProvider()]

    def _resolved_status(self) -> str:
        """Return the status that should be applied on every provider write."""
        if self.request.user.is_verified:
            return ListingStatus.PENDING
        return ListingStatus.DRAFT

    def perform_create(self, serializer) -> None:
        forced_status = self._resolved_status()
        listing = serializer.save(owner=self.request.user, status=forced_status)
        logger.info(
            "Provider %s created listing %s with status=%s.",
            self.request.user.email,
            listing.id,
            forced_status,
        )

    def perform_update(self, serializer) -> None:
        forced_status = self._resolved_status()
        listing = serializer.save(status=forced_status)
        logger.info(
            "Provider %s updated listing %s; status set to %s.",
            self.request.user.email,
            listing.id,
            forced_status,
        )
