from rest_framework import serializers

from apps.catalog.models import Listing, ListingCategory
from apps.users.enums import UserRole

from .models import ProviderProfile

# ---------------------------------------------------------------------------
# Provider Profile
# ---------------------------------------------------------------------------

_PROVIDER_CATEGORY_MAP: dict[str, str] = {
    UserRole.TUTOR: ListingCategory.TUTORING,
    UserRole.MASTERCLASS: ListingCategory.MASTERCLASSES,
}

_CATEGORY_ROLE_ERROR: dict[str, str] = {
    UserRole.TUTOR: "TUTOR providers can only create TUTORING listings.",
    UserRole.MASTERCLASS: (
        "MASTERCLASS providers can only create MASTERCLASSES listings."
    ),
}


class ProviderProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for GET/PATCH /api/v1/provider/profile/.

    Writable fields: display_name, bio, subjects, hourly_rate_qar, availability.
    Read-only fields: user_id, email, full_name, role, is_verified,
                      created_at, updated_at.
    """

    user_id = serializers.IntegerField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    is_verified = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProviderProfile
        fields = [
            "user_id",
            "email",
            "full_name",
            "role",
            "is_verified",
            "display_name",
            "bio",
            "subjects",
            "hourly_rate_qar",
            "availability",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


# ---------------------------------------------------------------------------
# Provider-owned Listings
# ---------------------------------------------------------------------------


class ProviderListingSerializer(serializers.ModelSerializer):
    """
    Serializer for the provider listing CRUD endpoints.

    Writable fields (what a provider can set):
        title, subtitle, neighborhood, lat, lng, price_from_qar,
        age_groups, image_urls, description, highlights, is_featured,
        category.

    Read-only (server-controlled):
        id, owner_id, status, rating, review_count, created_at, updated_at.

    Category constraint:
        TUTOR  → must use TUTORING category.
        MASTERCLASS → must use MASTERCLASSES category.
        Validated in validate_category(); also re-validated on update.

    Status rule:
        On every create/update the server forces:
            status = PENDING  if user.is_verified
            status = DRAFT    otherwise
        Any status value in the request body is silently ignored.
    """

    owner_id = serializers.SerializerMethodField(read_only=True)

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
            "description",
            "highlights",
            "is_featured",
            "rating",
            "review_count",
            "status",
            "owner_id",
            # Phase 5 private fields — writable by the provider, never in public API
            "session_schedule",
            "exact_address",
            "materials_required",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "rating",
            "review_count",
            "status",
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
        allowed = _PROVIDER_CATEGORY_MAP.get(user.role)
        if allowed is None:
            # Non-provider user — permission layer will catch this first,
            # but guard defensively.
            raise serializers.ValidationError(
                "Your role does not permit creating listings."
            )
        if value != allowed:
            raise serializers.ValidationError(_CATEGORY_ROLE_ERROR[user.role])
        return value
