from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.core.files.storage import default_storage

from apps.providers.models import TutorDetail, TutorSubject

from apps.catalog.models import Listing, ListingClient, ListingClientStatus

from apps.catalog.models import Listing, ListingImage



class ListingImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = ListingImage
        fields = ["id", "url", "position"]

    def get_url(self, obj):
        return default_storage.url(obj.key)

class ListingCardSerializer(serializers.ModelSerializer):
    """
    Serializer for the list endpoint (ListingCard shape per spec §9).

    Fields: id, title, category, subtitle, neighborhood, lat, lng,
            rating, review_count, price_from_qar, image_urls, age_groups,
            is_featured, distance_km.

    distance_km is an annotated float added by the view when lat/lng are
    provided; it is None when the annotation is absent or when the listing
    itself has null coordinates.
    """

    distance_km = serializers.SerializerMethodField()
    image_urls = serializers.SerializerMethodField()
    tags = serializers.SlugRelatedField(
        slug_field="name",
        many=True,
        read_only=True,
    )

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "category",
            "tags",
            "subtitle",
            "neighborhood",
            "lat",
            "lng",
            "rating",
            "review_count",
            "price_from_qar",
            "image_urls",
            "age_groups",
            "is_featured",
            "distance_km",
        ]

    def get_distance_km(self, obj: Listing) -> float | None:
        raw = getattr(obj, "distance_km", None)
        if raw is None:
            return None
        try:
            return round(float(raw), 2)
        except (TypeError, ValueError):
            return None

    def get_image_urls(self, obj):
        return [default_storage.url(img.key) for img in obj.images.all()]
    

class ListingDetailSerializer(ListingCardSerializer):
    """
    Serializer for the detail endpoint (ListingDetail shape per spec §9).

    Extends ListingCard with: description, highlights, owner_id, reviews.

    reviews embeds the 10 most-recent reviews (Phase 7). Full paginated list
    is at GET /api/v1/listings/{id}/reviews/.
    """

    owner_id = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    images = ListingImageSerializer(many=True, read_only=True)

    class Meta(ListingCardSerializer.Meta):
        fields = ListingCardSerializer.Meta.fields + [
            "description",
            "highlights",
            "owner_id",
            "reviews",
            "images"
        ]

    def get_owner_id(self, obj: Listing) -> str | None:
        pk = obj.owner_id
        return str(pk) if pk is not None else None

    def get_reviews(self, obj: Listing) -> list:
        from apps.reviews.serializers import ReviewListSerializer

        return ReviewListSerializer(
            obj.reviews.select_related("author").order_by("-created_at")[:10],
            many=True,
        ).data
    

class CategoryCountSerializer(serializers.Serializer):
    """Serializer for GET /api/v1/categories/ — {key, count}."""

    key = serializers.CharField()
    count = serializers.IntegerField()


class TutorSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorSubject
        fields = ["id", "name"]


class TutorCardSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = TutorDetail
        fields = [
            "id",
            "full_name",
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
        ]


class ListingClientSerializer(serializers.ModelSerializer):
    """
    Client-facing serializer (FAMILY role).

    Used by ListingClientViewSet to create and view a client's own requests.
    On create the client only supplies ``listing``; ``user`` and ``status``
    are set by the view. ``status`` is read-only here.
    """

    listing_title = serializers.CharField(source="listing.title", read_only=True)

    class Meta:
        model = ListingClient
        fields = ["id", "listing", "listing_title", "status", "created_at"]
        read_only_fields = ["id", "listing_title", "status", "created_at"]

    def validate_listing(self, listing: Listing) -> Listing:
        user = self.context["request"].user

        if listing.owner == user:
            raise serializers.ValidationError(
                "You cannot request your own listing."
            )

        if ListingClient.objects.filter(user=user, listing=listing).exists():
            raise serializers.ValidationError(
                "You have already requested this listing."
            )

        return listing


class ListingClientListSerializer(serializers.ModelSerializer):
    """
    Client-facing read serializer for the list endpoint.

    Embeds the full listing card so the app can render the listing alongside
    the request ``status`` without a second round-trip.
    """

    listing = ListingCardSerializer(read_only=True)

    class Meta:
        model = ListingClient
        fields = ["id", "listing", "status", "comment", "created_at", "updated_at"]


class ListingClientUserSerializer(serializers.ModelSerializer):
    """Minimal user info embedded in the owner-facing request list."""

    class Meta:
        model = get_user_model()
        fields = ["id", "full_name", "email", "phone"]


class ListingClientOwnerSerializer(serializers.ModelSerializer):
    """
    Owner-facing serializer (MASTERCLASS role).

    Used by ListingOwnerViewSet to list the clients who requested an owned
    listing and to PATCH the request ``status`` (accept / reject). Only
    ``status`` is writable; everything else is read-only.
    """

    user = ListingClientUserSerializer(read_only=True)
    listing_title = serializers.CharField(source="listing.title", read_only=True)

    class Meta:
        model = ListingClient
        fields = [
            "id",
            "user",
            "listing",
            "listing_title",
            "status",
            "comment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user",
            "listing",
            "listing_title",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        # Resolve the effective status after this (partial) update.
        status = attrs.get(
            "status",
            getattr(self.instance, "status", None),
        )
        comment = attrs.get(
            "comment",
            getattr(self.instance, "comment", ""),
        )
        if status == ListingClientStatus.REJECTED and not (comment or "").strip():
            raise serializers.ValidationError(
                {"comment": "A comment is required when rejecting a request."}
            )
        return attrs

