from urllib.parse import urlsplit

from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.catalog.models import (
    Listing,
    ListingCategory,
    ListingContact,
    MasterclassEventType,
)
from apps.catalog.serializers import ListingContactSerializer, ListingImageSerializer
from apps.providers.models import (
    AvatarImage,
    ProviderChoices,
    ProviderVerification,
    StatusChoices,
    TutorDetail,
    TutorStatus,
)
from apps.users.enums import UserRole

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
    email = serializers.EmailField(source="user.email", read_only=True)
    display_name = serializers.CharField(required=False, allow_blank=True)
    role = serializers.SerializerMethodField(read_only=True)
    avatar_url = serializers.SerializerMethodField(read_only=True)
    avatar = AvatarImageSerializer(many=False, read_only=True)

    class Meta:
        model = TutorDetail
        fields = [
            "user_id",
            "full_name",
            "email",
            "display_name",
            "role",
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
            "linkedin_url",
            "languages",
            "trial_available",
            "bio",
            "availability",
            "is_verified",
            "created_at",
            "updated_at",
            "city",
            "status",
        ]
        read_only_fields = [
            "rating",
            "review_count",
            "is_verified",
            "created_at",
            "updated_at",
        ]

    def get_role(self, obj: TutorDetail) -> str:
        return UserRole.TUTOR

    def to_representation(self, instance: TutorDetail) -> dict:
        representation = super().to_representation(instance)
        representation["display_name"] = instance.user.full_name
        return representation

    def validate_status(self, value: str) -> str:
        if value == TutorStatus.DELETED:
            raise serializers.ValidationError(
                "Only the server can delete a tutor profile."
            )
        return value

    def create(self, validated_data: dict) -> TutorDetail:
        display_name = validated_data.pop("display_name", None)
        detail = super().create(validated_data)
        if display_name is not None and detail.user.full_name != display_name:
            detail.user.full_name = display_name
            detail.user.save(update_fields=["full_name"])
        return detail

    def update(self, instance: TutorDetail, validated_data: dict) -> TutorDetail:
        display_name = validated_data.pop("display_name", None)
        detail = super().update(instance, validated_data)
        if display_name is not None and detail.user.full_name != display_name:
            detail.user.full_name = display_name
            detail.user.save(update_fields=["full_name"])
        return detail

    def get_avatar_url(self, obj: TutorDetail) -> str:
        avatar = getattr(obj, "avatar", None)
        return default_storage.url(avatar.key) if avatar else ""

    def validate_linkedin_url(self, value: str) -> str:
        if not value:
            return ""
        parts = urlsplit(value)
        hostname = (parts.hostname or "").lower()
        if parts.scheme not in {"http", "https"} or (
            hostname != "linkedin.com" and not hostname.endswith(".linkedin.com")
        ):
            raise serializers.ValidationError("Enter a valid LinkedIn URL.")
        return value


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
    contacts = ListingContactSerializer(many=True, required=False)
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
            "contacts",
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
            "registration_url",
            "event_type",
            "starts_at",
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
        attrs = super().validate(attrs)
        category = attrs.get(
            "category",
            getattr(self.instance, "category", None),
        )

        if category != ListingCategory.MASTERCLASSES:
            attrs["is_online"] = False
            attrs["meeting_url"] = ""
            attrs["registration_url"] = ""
            attrs["event_type"] = MasterclassEventType.ONGOING
            attrs["starts_at"] = None
            return attrs

        is_online = attrs.get("is_online", getattr(self.instance, "is_online", False))
        meeting_url = attrs.get("meeting_url", getattr(self.instance, "meeting_url", ""))
        neighborhood = attrs.get(
            "neighborhood", getattr(self.instance, "neighborhood", "")
        )

        # On a partial update (PATCH) only enforce a cross-field requirement
        # when one of the fields it depends on is actually part of the request,
        # so an unrelated change (e.g. just the title) is never blocked.
        partial = getattr(self, "partial", False)
        online_submitted = "is_online" in attrs or "meeting_url" in attrs
        offline_submitted = "is_online" in attrs or "neighborhood" in attrs

        if (not partial or online_submitted) and is_online and not meeting_url:
            raise serializers.ValidationError(
                {"meeting_url": "Required for online listings"}
            )
        if (not partial or offline_submitted) and not is_online and not neighborhood:
            raise serializers.ValidationError(
                {"neighborhood": "Required for offline listings"}
            )

        event_fields_submitted = (
            "category" in attrs or "event_type" in attrs or "starts_at" in attrs
        )
        if category == ListingCategory.MASTERCLASSES and (
            not partial or event_fields_submitted
        ):
            event_type = attrs.get(
                "event_type",
                getattr(
                    self.instance,
                    "event_type",
                    MasterclassEventType.ONGOING,
                ),
            )
            starts_at = attrs.get(
                "starts_at",
                getattr(self.instance, "starts_at", None),
            )
            if starts_at is None:
                raise serializers.ValidationError(
                    {"starts_at": "Choose when this masterclass will take place."}
                )
            if starts_at <= timezone.now():
                raise serializers.ValidationError(
                    {
                        "starts_at": (
                            "The masterclass date and time must be in the future."
                        )
                    }
                )
            if event_type not in MasterclassEventType.values:
                raise serializers.ValidationError({"event_type": "Invalid event type."})

        return attrs

    def validate_contacts(self, contacts):
        if len(contacts) > 20:
            raise serializers.ValidationError(
                "A listing cannot have more than 20 contacts."
            )

        seen = set()
        for contact in contacts:
            identity = (contact["contact_type"], contact["value"].casefold())
            if identity in seen:
                raise serializers.ValidationError(
                    "The same contact cannot be added more than once."
                )
            seen.add(identity)

        return contacts

    @transaction.atomic
    def create(self, validated_data):
        contacts_data = validated_data.pop("contacts", [])
        listing = super().create(validated_data)
        ListingContact.objects.bulk_create(
            [
                ListingContact(listing=listing, **contact_data)
                for contact_data in contacts_data
            ]
        )
        return listing

    @transaction.atomic
    def update(self, instance, validated_data):
        contacts_data = validated_data.pop("contacts", serializers.empty)
        listing = super().update(instance, validated_data)

        if contacts_data is not serializers.empty:
            listing.contacts.all().delete()
            ListingContact.objects.bulk_create(
                [
                    ListingContact(listing=listing, **contact_data)
                    for contact_data in contacts_data
                ]
            )

        return listing

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
    has_cv = serializers.SerializerMethodField()
    ai_screening_status = serializers.SerializerMethodField()

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
            "has_cv",
            "ai_screening_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_has_cv(self, obj: ProviderVerification) -> bool:
        return bool(obj.cv)

    def get_ai_screening_status(self, obj: ProviderVerification) -> str | None:
        screening = obj.ai_screenings.first()
        return screening.status if screening else None


class ProviderVerificationRequestSerializer(serializers.Serializer):
    provider_type = serializers.ChoiceField(choices=ProviderChoices.choices)
    cv = serializers.FileField(required=False)
    ai_processing_consent = serializers.BooleanField(required=False)

    def validate(self, attrs: dict) -> dict:
        cv = attrs.get("cv")
        if attrs["provider_type"] == ProviderChoices.MASTERCLASS:
            if attrs.get("ai_processing_consent") is not True:
                raise serializers.ValidationError(
                    {"ai_processing_consent": "Consent to AI CV processing is required."}
                )
            if cv is None:
                raise serializers.ValidationError(
                    {"cv": "A PDF CV is required for masterclass applications."}
                )
            if not cv.name.lower().endswith(".pdf"):
                raise serializers.ValidationError({"cv": "The CV must be a PDF file."})
            if cv.size > 10 * 1024 * 1024:
                raise serializers.ValidationError(
                    {"cv": "The CV must be 10 MB or smaller."}
                )
            header = cv.read(5)
            cv.seek(0)
            if header != b"%PDF-":
                raise serializers.ValidationError(
                    {"cv": "The CV must be a valid PDF file."}
                )
        return attrs


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
