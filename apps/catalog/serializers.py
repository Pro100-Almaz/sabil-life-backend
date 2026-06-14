from rest_framework import serializers

from .models import Listing


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
        except TypeError, ValueError:
            return None


class ListingDetailSerializer(ListingCardSerializer):
    """
    Serializer for the detail endpoint (ListingDetail shape per spec §9).

    Extends ListingCard with: description, highlights, owner_id, reviews.

    reviews is an empty list for now — the Review model is built in Phase 7.
    TODO (Phase 7): replace the static [] with a nested ReviewSerializer when
    the Review FK target exists.
    """

    owner_id = serializers.SerializerMethodField()
    # TODO (Phase 7): replace with ReviewSerializer(many=True, read_only=True)
    reviews = serializers.ListField(child=serializers.DictField(), read_only=True)

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

    def to_representation(self, instance: Listing) -> dict:
        data = super().to_representation(instance)
        # reviews is not a model field — inject the static placeholder
        data["reviews"] = []
        return data


class CategoryCountSerializer(serializers.Serializer):
    """Serializer for GET /api/v1/categories/ — {key, count}."""

    key = serializers.CharField()
    count = serializers.IntegerField()
