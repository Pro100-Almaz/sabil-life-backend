import logging
import uuid 

from pathlib import Path
from django.core.files.storage import default_storage
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, mixins, permissions, viewsets, status, views, serializers
import rest_framework.exceptions
from rest_framework import parsers
import rest_framework.status
from rest_framework.response import Response

from apps.catalog.models import Listing, ListingStatus, ListingImage
from apps.catalog.serializers import ListingImageSerializer
from apps.catalog.services import delete_listing, delete_listing_image
from apps.users.enums import UserRole
from apps.users.models import Role

from apps.providers.models import (
    ProviderChoices,
    ProviderVerification,
    StatusChoices,
    TutorDetail,
    AvatarImage
)
from apps.providers.permissions import IsListingOwner
from apps.providers.schema import (
    PROVIDER_LISTING_CREATE_SCHEMA,
    PROVIDER_LISTING_DESTROY_SCHEMA,
    PROVIDER_LISTING_LIST_SCHEMA,
    PROVIDER_LISTING_RETRIEVE_SCHEMA,
    PROVIDER_LISTING_UPDATE_SCHEMA,
)
from apps.providers.serializers import (
    AvatarImageSerializer,
    ProviderListingSerializer,
    ProviderVerificationReviewSerializer,
    TutorDetailSerializer,
    VerifyProviderSerializer,
)
from apps.providers.services import apply_verification_outcome, delete_avatar_image
from apps.users.permissions import IsManagerOrAdmin, IsMasterclassManagerOrAdmin


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tutor Detail
# ---------------------------------------------------------------------------


class TutorDetailView(generics.CreateAPIView, generics.RetrieveUpdateAPIView):
    """
    GET    /api/v1/provider/tutor-detail/ — retrieve own tutor detail.
    POST   /api/v1/provider/tutor-detail/ — create tutor detail.
    PATCH  /api/v1/provider/tutor-detail/ — update tutor detail.
    DELETE /api/v1/provider/tutor-detail/ — soft-delete tutor detail and remove TUTOR role.

    Auth: IsAuthenticated + IsTutor.
    Avatar is uploaded as a file (multipart/form-data).
    """

    serializer_class = TutorDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    parser_classes = [
        parsers.MultiPartParser,
        parsers.FormParser,
        parsers.JSONParser,
    ]

    def get_object(self) -> TutorDetail:
        try:
            obj = TutorDetail.objects.get(user=self.request.user, deleted_at__isnull=True)
        except TutorDetail.DoesNotExist:
            raise rest_framework.exceptions.NotFound("Tutor detail not found.")
        self.check_object_permissions(self.request, obj)
        return obj

    def _sync_verification(self, new_status: str) -> None:
        """
        Keep the provider's TUTOR verification record in step with their
        tutor detail submissions:

        - first submission (create)  → PENDING (fresh request for review)
        - any later edit (update)    → UPDATED (re-submitted for review)

        Either way the previous reviewer comment is cleared, so a stale
        rejection reason never lingers on a freshly re-submitted request.
        """
        verification, created = ProviderVerification.objects.get_or_create(
            user=self.request.user,
            provider_type=ProviderChoices.TUTOR,
            defaults={"status": new_status},
        )
        if not created:
            if verification.status != StatusChoices.APPROVED:
                verification.status = new_status
            verification.comment = ""
            verification.save(update_fields=["status", "comment", "updated_at"])
        logger.info(
            "Tutor %s verification set to %s.", self.request.user.email, new_status
        )

    def perform_create(self, serializer) -> None:
        serializer.save(user=self.request.user)
        self._sync_verification(StatusChoices.PENDING)

    def perform_update(self, serializer) -> None:
        serializer.save()
        self._sync_verification(StatusChoices.UPDATED)

    def create(self, request, *args, **kwargs):
        if TutorDetail.objects.filter(user=request.user, deleted_at__isnull=True).exists():
            return Response(
                {"detail": "Tutor detail already exists. Use PATCH to update."},
                status=rest_framework.status.HTTP_409_CONFLICT,
            )
        return super().create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        detail = self.get_object()
        detail.deleted_at = timezone.now()
        detail.save(update_fields=["deleted_at", "updated_at"])

        user = request.user
        tutor_role = Role.objects.filter(name=UserRole.TUTOR).first()
        if tutor_role:
            user.roles.remove(tutor_role)
            if hasattr(user, "_role_names_cache"):
                del user._role_names_cache

        logger.info("Tutor %s soft-deleted their tutor detail.", user.email)
        return Response(status=rest_framework.status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Avatar Upload
# ---------------------------------------------------------------------------


class AvatarUploadView(views.APIView):
    """
    POST /api/v1/provider/avatar/ — upload/replace tutor avatar.

    Returns {"id", "url"}.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def _get_tutor(self, request):
        try:
            obj, _ = TutorDetail.objects.get_or_create(user=request.user)
        except TutorDetail.DoesNotExist:
            raise rest_framework.exceptions.NotFound("Tutor not found")
        
        return obj 
    
    def post(self, request):
        tutor = self._get_tutor(request=request)
        ProviderVerification.objects.get_or_create(
            user=request.user,
            provider_type=ProviderChoices.TUTOR,
            defaults={"status": StatusChoices.PENDING},
        )
        f = request.FILES.get("avatar")
        if not f:
            return Response({"avatar": ["No file provided."]}, status=400)

        # replace existing avatar (row + storage object)
        old = AvatarImage.objects.filter(tutor=tutor).first()
        if old:
            delete_avatar_image(old)

        suffix = Path(f.name).suffix.lower()
        object_name = f"avatars/{tutor.id}/{uuid.uuid4().hex}{suffix}"
        key = default_storage.save(object_name, f)
        avatar = AvatarImage.objects.create(tutor=tutor, key=key)
        return Response(AvatarImageSerializer(avatar).data, status=201)
    
    def delete(self, request):
        tutor = self._get_tutor(request=request)
        avatar = AvatarImage.objects.filter(tutor=tutor).first()
        if avatar:
            delete_avatar_image(avatar)

        return Response(status=status.HTTP_204_NO_CONTENT)
    

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
    permission_classes = [permissions.IsAuthenticated, IsMasterclassManagerOrAdmin]
    lookup_field = "id"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    parser_classes = [
        rest_framework.parsers.MultiPartParser,
        rest_framework.parsers.FormParser,
        rest_framework.parsers.JSONParser,
    ]

    def get_queryset(self):
        return Listing.objects.filter(owner=self.request.user).prefetch_related("images").prefetch_related("tags")

    def perform_destroy(self, instance):
        # Explicit storage cleanup: remove the listing and its images' MinIO
        # objects together (replaces the old post_delete signal).
        delete_listing(instance)

    def get_permissions(self):
        if self.action in {"retrieve", "partial_update", "destroy"}:
            return [
                permissions.IsAuthenticated(),
                IsMasterclassManagerOrAdmin(),
                IsListingOwner(),
            ]
        return [permissions.IsAuthenticated(), IsMasterclassManagerOrAdmin()]

    def _resolved_status(self) -> str:
        """Return the status that should be applied on every provider write."""
        status = self.request.query_params.get('status', 'DRAFT').upper()
        if status not in {'DRAFT', 'PENDING'}:
            raise serializers.ValidationError({"status": f"Unsupported status '{status}'."})
        
        if self.request.user.is_verified and status != ListingStatus.DRAFT:
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


class VerifyProviderView(generics.ListAPIView):
    """
    GET  /api/v1/provider/verify/ — list the authenticated provider's own
    verification records. Each record exposes its current ``status`` and,
    when the request was rejected, the reviewer's ``comment``.

    POST /api/v1/provider/verify/ — request verification for a provider type.
    Body: ``{"provider_type": "MASTERCLASS"}``.

    A TUTOR verification is normally created automatically when the tutor
    detail form is submitted; this POST is the entry point for provider
    types that have no detail form (e.g. MASTERCLASS), and also lets a
    provider re-request after a rejection or cancellation.

    Auth: IsAuthenticated + IsProvider (TUTOR or MASTERCLASS).
    """

    serializer_class = VerifyProviderSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return ProviderVerification.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        provider_type = (request.data.get("provider_type") or "").upper()
        if provider_type not in ProviderChoices.values:
            return Response(
                {"provider_type": [f"Unknown provider type '{provider_type}'."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        verification, created = ProviderVerification.objects.get_or_create(
            user=request.user,
            provider_type=provider_type,
            defaults={"status": StatusChoices.PENDING},
        )

        if created:
            logger.info(
                "Provider %s requested %s verification.",
                request.user.email,
                provider_type,
            )
            return Response(
                VerifyProviderSerializer(verification).data,
                status=status.HTTP_201_CREATED,
            )

        # A record already exists. Re-requesting is only allowed from a
        # terminal-but-not-approved state (rejected / cancelled).
        if verification.status in (StatusChoices.REJECTED, StatusChoices.CANCELLED):
            verification.status = StatusChoices.UPDATED
            verification.comment = ""
            verification.save(update_fields=["status", "comment", "updated_at"])
            logger.info(
                "Provider %s re-requested %s verification.",
                request.user.email,
                provider_type,
            )
            return Response(VerifyProviderSerializer(verification).data)

        detail = (
            "This provider type is already verified."
            if verification.status == StatusChoices.APPROVED
            else "A verification request is already pending review."
        )
        return Response(
            {"detail": detail, **VerifyProviderSerializer(verification).data},
            status=status.HTTP_409_CONFLICT,
        )

    def delete(self, request, *args, **kwargs):
        provider_type = kwargs["provider_type"].upper()
        if provider_type not in ProviderChoices.values:
            return Response(
                {"detail": f"Unknown provider type '{provider_type}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            verification = ProviderVerification.objects.get(
                user=request.user, provider_type=provider_type
            )
        except ProviderVerification.DoesNotExist:
            raise rest_framework.exceptions.NotFound(
                "No verification request found for this provider type."
            )

        if verification.status == StatusChoices.APPROVED:
            return Response(
                {"detail": "An approved verification cannot be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if verification.status != StatusChoices.CANCELLED:
            verification.delete()
            if provider_type == ProviderChoices.TUTOR.value:
                TutorDetail.objects.filter(user=request.user).delete()
            logger.info(
                "Provider %s cancelled their %s verification.",
                request.user.email,
                provider_type,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class ProviderVerificationAdminViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Manager/admin review of provider verification requests.

    GET   /api/v1/provider/verify/admin/        — list all requests
    GET   /api/v1/provider/verify/admin/{id}/   — retrieve one request
    PATCH /api/v1/provider/verify/admin/{id}/   — approve / reject a request

    The list endpoint accepts optional ?status= and ?provider_type= filters.

    On PATCH the reviewer may only set status to APPROVED or REJECTED, a
    rejection must include a comment, and a CANCELLED request can no longer
    be touched (enforced in ProviderVerificationReviewSerializer).

    Approving grants the matching provider role (TUTOR / MASTERCLASS) on the
    user's roles M2M; rejecting revokes it. For TUTOR the TutorDetail.is_verified
    mirror flag is kept in step so the tutor-detail API stays truthful.

    Auth: IsAuthenticated + IsManagerOrAdmin.
    """

    permission_classes = [permissions.IsAuthenticated, IsManagerOrAdmin]
    http_method_names = ["get", "patch", "head", "options"]
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.action == "partial_update":
            return ProviderVerificationReviewSerializer
        return VerifyProviderSerializer

    def get_queryset(self):
        qs = ProviderVerification.objects.select_related("user").all()
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param.upper())
        provider_type = self.request.query_params.get("provider_type")
        if provider_type:
            qs = qs.filter(provider_type=provider_type.upper())
        return qs

    def perform_update(self, serializer) -> None:
        verification = serializer.save()
        
        # The verification outcome is expressed by granting (or revoking) the
        # matching provider role on the user's roles M2M. ProviderChoices
        # values map 1:1 to UserRole values ("TUTOR" / "MASTERCLASS").
        apply_verification_outcome(verification, self.request.user)

    def update(self, request, *args, **kwargs):
        # Force PATCH semantics — the router only exposes patch, but guard anyway.
        kwargs["partial"] = True
        response = super().update(request, *args, **kwargs)
        # Return the full read representation after a successful review.
        instance = self.get_object()
        return Response(VerifyProviderSerializer(instance).data)


class ListingImageView(views.APIView):
    """POST /provider/listings/<listing_id>/images/ -upload one or more"""
    permission_classes = [permissions.IsAuthenticated, IsMasterclassManagerOrAdmin]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def _get_listing(self, request, listing_id):
        try:
            obj = Listing.objects.get(id=listing_id, owner=request.user)
        except Listing.DoesNotExist:
            raise rest_framework.exceptions.NotFound("Listing not found")
        
        return obj 
    
    def post(self, request, listing_id):
        listing = self._get_listing(request=request, listing_id=listing_id)
        files = request.FILES.getlist("images")
        created = []
        start = listing.images.count()
        for i, f in enumerate(files):
            suffix = Path(f.name).suffix.lower()
            object_name = f"listings/{listing_id}/{uuid.uuid4().hex}{suffix}"
            key = default_storage.save(object_name, f)
            created.append(ListingImage.objects.create(listing=listing, key=key, position=start + i))
        return Response(ListingImageSerializer(created, many=True).data, status=201)
    

class ListingImageDetailView(generics.DestroyAPIView):
    """DELETE /provider/listing/<listing_id>/images/<image_id>"""
    permission_classes = [permissions.IsAuthenticated, IsMasterclassManagerOrAdmin]

    def _get_listing(self, request, listing_id, image_id):
        try:
            listing = Listing.objects.get(id=listing_id, owner=request.user)
            obj = ListingImage.objects.get(id=image_id, listing=listing)
        except (ListingImage.DoesNotExist, Listing.DoesNotExist):
            raise rest_framework.exceptions.NotFound("Image or Listing not found.")
        
        return obj 

    def delete(self, request, listing_id, image_id):
        image = self._get_listing(request, listing_id, image_id)
        delete_listing_image(image)
        return Response(status=204)