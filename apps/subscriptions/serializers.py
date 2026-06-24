"""
Subscription serializers — Phase 5.

Two serializer shapes:
  FamilySubscriptionSerializer   — family viewing their own subscriptions.
                                    Includes listing_private_details.
  ProviderSubscriptionSerializer — provider viewing their roster.
                                    Shows family id + full_name only (no contact).

Contact deferral note (Phase 5):
  Provider sees family.full_name but NOT phone or email. Phase 6 may unlock
  contact details via the same reveal mechanism as inquiries.
  # TODO Phase 6: unlock phone/email on provider side if reveal is gated here too.
"""

from rest_framework import serializers

from apps.subscriptions.models import MasterclassSubscription


class ListingPrivateDetailsSerializer(serializers.Serializer):
    """Nested serializer for private listing details exposed to subscribers."""

    session_schedule = serializers.CharField()
    exact_address = serializers.CharField()
    materials_required = serializers.ListField(child=serializers.CharField())


class FamilySubscriptionSerializer(serializers.ModelSerializer):
    """
    Serializer for the family-side subscription endpoints.

    Includes listing_private_details because that is the key value proposition
    of subscribing — the family gains access to private logistics information.
    """

    listing_id = serializers.UUIDField(read_only=True)
    provider_id = serializers.SerializerMethodField()
    listing_private_details = serializers.SerializerMethodField()

    class Meta:
        model = MasterclassSubscription
        fields = [
            "id",
            "listing_id",
            "provider_id",
            "status",
            "cancelled_at",
            "created_at",
            "updated_at",
            "listing_private_details",
        ]
        read_only_fields = fields

    def get_provider_id(self, obj: MasterclassSubscription) -> str | None:
        pk = obj.provider_id
        return str(pk) if pk is not None else None

    def get_listing_private_details(self, obj: MasterclassSubscription) -> dict:
        listing = obj.listing
        return {
            "session_schedule": listing.session_schedule,
            "exact_address": listing.exact_address,
            "materials_required": listing.materials_required,
        }


class ProviderSubscriptionSerializer(serializers.ModelSerializer):
    """
    Serializer for the provider-side subscription endpoints.

    Provider sees who subscribed (family id + full_name) for roster purposes.
    Contact details (phone, email) are deferred to Phase 6.
    # TODO Phase 6: unlock phone/email for provider if subscription tier gates it.
    """

    listing_id = serializers.UUIDField(read_only=True)
    listing_title = serializers.SerializerMethodField()
    family = serializers.SerializerMethodField()

    class Meta:
        model = MasterclassSubscription
        fields = [
            "id",
            "listing_id",
            "listing_title",
            "family",
            "status",
            "cancelled_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_listing_title(self, obj: MasterclassSubscription) -> str:
        return obj.listing.title if obj.listing_id else ""

    def get_family(self, obj: MasterclassSubscription) -> dict:
        return {
            "id": str(obj.family_id),
            "full_name": obj.family.full_name if obj.family_id else None,
        }


class SubscriptionCreateSerializer(serializers.Serializer):
    """Input serializer for POST /api/v1/subscriptions/."""

    listing_id = serializers.UUIDField()
