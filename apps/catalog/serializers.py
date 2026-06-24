from rest_framework import serializers

from apps.providers.models import TutorDetail, TutorSubject

from apps.catalog.models import Listing


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


class ListingDetailSerializer(ListingCardSerializer):
    """
    Serializer for the detail endpoint (ListingDetail shape per spec §9).

    Extends ListingCard with: description, highlights, owner_id, reviews.

    reviews embeds the 10 most-recent reviews (Phase 7). Full paginated list
    is at GET /api/v1/listings/{id}/reviews/.
    """

    owner_id = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()

    class Meta(ListingCardSerializer.Meta):
        fields = ListingCardSerializer.Meta.fields + [
            "description",
            "highlights",
            "owner_id",
            "reviews",
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
    id = serializers.IntegerField(source="user.id", read_only=True)
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
