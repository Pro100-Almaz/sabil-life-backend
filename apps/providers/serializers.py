from django.core.files.storage import default_storage
from rest_framework import serializers

from apps.catalog.models import Listing, ListingCategory
from apps.catalog.serializers import ListingImageSerializer
from apps.users.enums import UserRole

from apps.providers.models import ProviderVerification, StatusChoices, TutorDetail, AvatarImage

# ---------------------------------------------------------------------------
# Provider Listings — shared maps
# ---------------------------------------------------------------------------

_PROVIDER_CATEGORY_MAP: dict[str, str] = {
    # UserRole.TUTOR: ListingCategory.TUTORING,
    UserRole.MASTERCLASS: ListingCategory.MASTERCLASSES,
}

_CATEGORY_ROLE_ERROR: dict[str, str] = {
    UserRole.TUTOR: "TUTOR providers can only create TUTORING listings.",
    UserRole.MASTERCLASS: (
        "MASTERCLASS providers can only create MASTERCLASSES listings."
    ),
}


# ---------------------------------------------------------------------------
# Tutor Detail
# ---------------------------------------------------------------------------


class AvatarImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = AvatarImage
        fields = ["id", "url"]

    def get_url(self, obj):
        return default_storage.url(obj.key)


class TutorDetailSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    avatar_url = serializers.SerializerMethodField(read_only=True)
    avatar = AvatarImageSerializer(many=False, read_only=True)
    
    class Meta:
        model = TutorDetail
        fields = [
            "user_id",
            "full_name",
            "avatar_url",
            "avatar",
            "affiliation_listing_id",
            "subjects",
            "formats",
            "age_groups",
            "price_per_hour_qar",
            "rating",
            "review_count",
            "years_experience",
            "credentials",
            "languages",
            "trial_available",
            "bio",
            "is_verified",
            "created_at",
            "updated_at",
            "city",
        ]
        read_only_fields = [
            "rating",
            "review_count",
            "is_verified",
            "created_at",
            "updated_at",
        ]

    def get_avatar_url(self, obj: TutorDetail) -> str:
        avatar = getattr(obj, "avatar", None)
        return default_storage.url(avatar.key) if avatar else ""


# ---------------------------------------------------------------------------
# Provider-owned Listings
# ---------------------------------------------------------------------------


class ProviderListingSerializer(serializers.ModelSerializer):
    """
    Serializer for the provider listing CRUD endpoints.

    Writable fields (what a provider can set):
        title, subtitle, neighborhood, lat, lng, price_from_qar,
        age_groups, image_urls, description, highlights, is_featured,
        category, status.

    Read-only (server-controlled):
        id, owner_id, rating, review_count, created_at, updated_at.

    Category constraint:
        MASTERCLASS → must use MASTERCLASSES category.
        MANAGER / ADMIN → may use any category.
        Tutors cannot create listings at all (blocked at the view permission).
        Validated in validate_category(); also re-validated on update.

    Status rule:
        On every create/update the server forces:
            status = PENDING  if user.is_verified
            status = DRAFT    otherwise
        Any status value in the request body is silently ignored.
    """

    owner_id = serializers.SerializerMethodField(read_only=True)
    images = ListingImageSerializer(many=True, read_only=True)
    image_urls = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "category",
            "subtitle",
            "neighborhood",
            "lat",
            "lng",
            "price_from_qar",
            "age_groups",
            "image_urls",
            "images",
            "description",
            "highlights",
            "is_featured",
            "rating",
            "review_count",
            "status",
            "owner_id",
            "session_schedule",
            "exact_address",
            "materials_required",
            "created_at",
            "updated_at",
            "is_online",
            "meeting_url",
        ]
        read_only_fields = [
            "id",
            "rating",
            "review_count",
            "owner_id",
            "created_at",
            "updated_at",
        ]

    def get_owner_id(self, obj: Listing) -> str | None:
        pk = obj.owner_id
        return str(pk) if pk is not None else None

    def _get_request_user(self):
        request = self.context.get("request")
        return request.user if request else None

    def validate_category(self, value: str) -> str:
        user = self._get_request_user()
        if user is None:
            return value
        # Managers and admins may create listings in any category.
        if user.has_any_role(UserRole.MANAGER, UserRole.ADMIN):
            return value
        allowed_categories = set()
        for role_key, cat in _PROVIDER_CATEGORY_MAP.items():
            if user.has_role(role_key):
                allowed_categories.add(cat)
        if not allowed_categories:
            raise serializers.ValidationError(
                "Your role does not permit creating listings."
            )
        if value not in allowed_categories:
            raise serializers.ValidationError(
                f"Your roles do not allow creating listings in the {value} category."
            )
        return value

    def validate(self, attrs):
        is_online = attrs.get("is_online", getattr(self.instance, "is_online", False))
        meeting_url = attrs.get("meeting_url", getattr(self.instance, "meeting_url", ""))
        neighborhood = attrs.get("neighborhood", getattr(self.instance, "neighborhood", ""))

        # On a partial update (PATCH) only enforce a cross-field requirement
        # when one of the fields it depends on is actually part of the request,
        # so an unrelated change (e.g. just the title) is never blocked.
        partial = getattr(self, "partial", False)
        online_submitted = "is_online" in attrs or "meeting_url" in attrs
        offline_submitted = "is_online" in attrs or "neighborhood" in attrs

        if (not partial or online_submitted) and is_online and not meeting_url:
            raise serializers.ValidationError({"meeting_url": "Required for online listings"})
        if (not partial or offline_submitted) and not is_online and not neighborhood:
            raise serializers.ValidationError({"neighborhood": "Required for offline listings"})

        return attrs

    def get_image_urls(self, obj):
        return [default_storage.url(img.key) for img in obj.images.all()]

# ---------------------------------------------------------------------------
# Provider Verification
# ---------------------------------------------------------------------------


class VerifyProviderSerializer(serializers.ModelSerializer):
    """
    Read serializer for a provider's verification record.

    Used by both the provider-facing GET (so the provider can see their
    status and, if rejected, the reviewer's comment) and the admin list/
    retrieve endpoints. Every field is read-only here — state transitions
    happen via dedicated endpoints/serializers.
    """

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = ProviderVerification
        fields = [
            "id",
            "user_id",
            "email",
            "full_name",
            "provider_type",
            "status",
            "comment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ProviderVerificationReviewSerializer(serializers.ModelSerializer):
    """
    Admin/manager serializer to APPROVE or REJECT a verification.

    Rules:
      - status may only be set to APPROVED or REJECTED.
      - a REJECTED verification must carry a comment explaining why.
      - a CANCELLED verification can no longer be reviewed.
    """

    class Meta:
        model = ProviderVerification
        fields = ["status", "comment"]

    def validate_status(self, value: str) -> str:
        if value not in (StatusChoices.APPROVED, StatusChoices.REJECTED):
            raise serializers.ValidationError(
                "Reviewers may only set status to APPROVED or REJECTED."
            )
        return value

    def validate(self, attrs: dict) -> dict:
        if self.instance and self.instance.status == StatusChoices.CANCELLED:
            raise serializers.ValidationError(
                "This verification was cancelled by the provider and can no "
                "longer be reviewed."
            )

        status_value = attrs.get("status", getattr(self.instance, "status", None))
        comment = (attrs.get("comment") or "").strip()
        if status_value == StatusChoices.REJECTED and not comment:
            raise serializers.ValidationError(
                {"comment": "A comment explaining the rejection is required."}
            )
        # Clear any stale rejection note when approving.
        if status_value == StatusChoices.APPROVED:
            attrs["comment"] = comment
        return attrs
