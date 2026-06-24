"""
Review serializers — Phase 7.

Three shapes:
  ReviewListSerializer   — public read. Exposes author_id but never author.email.
  ReviewCreateSerializer — family POST. Validates engagement gate + uniqueness.
  ReviewUpdateSerializer — family PATCH. Updates rating/text only.
"""

from django.db import IntegrityError
from rest_framework import serializers

from apps.reviews.models import Review
from apps.reviews.services import can_review


class ReviewListSerializer(serializers.ModelSerializer):
    """
    Public read serializer — safe to expose without authentication.

    author_name is author.full_name, falling back to "Anonymous" if blank.
    author.email is intentionally excluded.
    """

    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["id", "rating", "text", "author_name", "created_at", "author_id"]
        read_only_fields = fields

    def get_author_name(self, obj: Review) -> str:
        name = getattr(obj.author, "full_name", "") or ""
        return name.strip() or "Anonymous"


class ReviewCreateSerializer(serializers.Serializer):
    """
    Input serializer for POST /api/v1/listings/{listing_id}/reviews/.

    Validates:
    1. rating is 1-5.
    2. Engagement gate: family must have evidence of engagement for
       TUTORING / MASTERCLASSES listings (see services.can_review).
    3. Uniqueness: one review per (listing, author). Converts IntegrityError
       to a 409-friendly ValidationError that the view catches.
    """

    rating = serializers.IntegerField(min_value=1, max_value=5)
    text = serializers.CharField(allow_blank=True, default="", required=False)

    def validate(self, attrs):
        request = self.context.get("request")
        listing = self.context.get("listing")

        if request and listing and not can_review(request.user, listing):
            raise serializers.ValidationError(
                {
                    "non_field_errors": [
                        "You haven't engaged with this listing yet. "
                        "For tutoring listings you need an accepted or "
                        "completed inquiry; for masterclass listings you "
                        "need an active or past subscription."
                    ]
                }
            )
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        listing = self.context["listing"]
        try:
            return Review.objects.create(
                listing=listing,
                author=request.user,
                rating=validated_data["rating"],
                text=validated_data.get("text", ""),
            )
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"non_field_errors": ["You have already reviewed this listing."]}
            ) from exc


class ReviewUpdateSerializer(serializers.ModelSerializer):
    """
    Input serializer for PATCH /api/v1/reviews/{id}/.

    Only rating and text are updatable. No uniqueness re-check needed.
    """

    class Meta:
        model = Review
        fields = ["rating", "text"]
        extra_kwargs = {
            "rating": {"min_value": 1, "max_value": 5},
            "text": {"allow_blank": True, "required": False},
        }
