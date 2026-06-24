"""
Inquiry serializers — Phase 5.

Two serializer shapes:
  FamilyInquirySerializer   — family viewing their own inquiry (no contact data).
  ProviderInquirySerializer — provider viewing received inquiry with redacted
                               family contact block.

Contact redaction pattern (Phase 5):
  family.full_name, phone, email are always null because contact_revealed is
  always False in Phase 5. The keys are always present so the client shape is
  stable. Phase 6 will change the conditional from "always None" to
  "real value when contact_revealed=True".
  # TODO Phase 6: flip null-stub to real values when contact_revealed=True.
"""

from rest_framework import serializers

from apps.inquiries.models import Inquiry


class FamilyInquirySerializer(serializers.ModelSerializer):
    """
    Serializer for the family-side inquiry endpoints.

    Returns inquiry data from the family's perspective. No family contact
    information is included (the family is looking at their own data).
    """

    listing_id = serializers.UUIDField(read_only=True)
    provider_id = serializers.SerializerMethodField()

    class Meta:
        model = Inquiry
        fields = [
            "id",
            "listing_id",
            "provider_id",
            "status",
            "message",
            "contact_revealed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_provider_id(self, obj: Inquiry) -> str | None:
        pk = obj.provider_id
        return str(pk) if pk is not None else None


class ProviderInquirySerializer(serializers.ModelSerializer):
    """
    Serializer for the provider-side inquiry endpoints.

    Includes a nested `family` block with contact fields. In Phase 5 contact
    fields are always null regardless of contact_revealed value — the key shape
    is stable for the client.

    # TODO Phase 6: when contact_revealed=True, replace nulls with real values
    # from obj.family (full_name, phone, email).
    """

    listing_id = serializers.UUIDField(read_only=True)
    provider_id = serializers.SerializerMethodField()
    family = serializers.SerializerMethodField()

    class Meta:
        model = Inquiry
        fields = [
            "id",
            "listing_id",
            "provider_id",
            "family",
            "status",
            "message",
            "contact_revealed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_provider_id(self, obj: Inquiry) -> str | None:
        pk = obj.provider_id
        return str(pk) if pk is not None else None

    def get_family(self, obj: Inquiry) -> dict:
        """
        Return a stable family contact block.

        When contact_revealed=True (free-trial flag or Phase 6 billing gate
        satisfied), real values are returned. Otherwise all contact fields
        are null so the client shape is always stable.
        See docs/PHASE_6_BILLING.md for the full billing-gate design.
        """
        base: dict = {
            "id": str(obj.family_id),
            "full_name": None,
            "phone": None,
            "email": None,
        }
        if obj.contact_revealed:
            base.update(
                {
                    "full_name": obj.family.full_name,
                    "phone": obj.family.phone,
                    "email": obj.family.email,
                }
            )
        return base


class InquiryCreateSerializer(serializers.Serializer):
    """Input serializer for POST /api/v1/inquiries/."""

    listing_id = serializers.UUIDField()
    message = serializers.CharField(min_length=1)
