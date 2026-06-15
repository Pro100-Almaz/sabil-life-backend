"""
Suggestion serializers — Phase 5.

`admin_notes` is intentionally excluded from all family-facing serializers.
It is only accessible via the Django admin panel.
"""

from rest_framework import serializers

from .models import ServiceSuggestion


class SuggestionSerializer(serializers.ModelSerializer):
    """
    Read serializer for family-side endpoints.

    admin_notes is NOT included — family must never see internal notes.
    """

    class Meta:
        model = ServiceSuggestion
        fields = [
            "id",
            "category",
            "neighborhood",
            "message",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class SuggestionCreateSerializer(serializers.ModelSerializer):
    """
    Input serializer for POST /api/v1/suggestions/.

    `message` is required. `category` and `neighborhood` are optional.
    `admin_notes` and `status` are server-controlled — not accepted from client.
    """

    class Meta:
        model = ServiceSuggestion
        fields = ["category", "neighborhood", "message"]
        extra_kwargs = {
            "category": {"required": False, "allow_blank": True},
            "neighborhood": {"required": False, "allow_blank": True},
            "message": {"required": True},
        }
