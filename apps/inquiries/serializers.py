"""
Inquiry serializers.

Serializer shapes:
  FamilyInquirySerializer   — family viewing their own inquiry. Includes a small
                              `tutor` block so the family knows who they wrote to.
  TutorInquirySerializer    — tutor viewing a received inquiry with a redacted
                              family contact block.
  InquiryCreateSerializer   — family input for creating an inquiry.
  InquiryStatusUpdateSerializer — tutor input for updating an inquiry's status.

Contact redaction pattern (Phase 5):
  family.full_name, phone, email are always null because contact_revealed is
  always False in Phase 5. The keys are always present so the client shape is
  stable. Phase 6 will change the conditional from "always None" to
  "real value when contact_revealed=True".
  # TODO Phase 6: flip null-stub to real values when contact_revealed=True.
"""

from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from apps.inquiries.models import Inquiry, InquiryStatus
from apps.inquiries.services import TUTOR_SETTABLE_STATUSES
from apps.providers.models import TutorDetail
from apps.reviews.models import TutorReview


def _tutor_block(obj: Inquiry) -> dict:
    """Small, public tutor summary embedded in inquiry responses."""
    tutor = obj.tutor
    return {
        "id": tutor.id,
        "full_name": tutor.user.full_name,
        "subjects": tutor.subjects,
        "is_verified": tutor.is_verified,
    }


class FamilyInquirySerializer(serializers.ModelSerializer):
    """
    Serializer for the family-side inquiry endpoints.

    Returns inquiry data from the family's perspective. No family contact
    information is included (the family is looking at their own data); a small
    `tutor` block identifies the addressed tutor.
    """

    tutor_id = serializers.IntegerField(source="tutor.id", read_only=True)
    tutor = serializers.SerializerMethodField()
    review = serializers.SerializerMethodField()

    class Meta:
        model = Inquiry
        fields = [
            "id",
            "tutor_id",
            "tutor",
            "status",
            "message",
            "contact_revealed",
            "created_at",
            "updated_at",
            "review",
        ]
        read_only_fields = fields

    def get_tutor(self, obj: Inquiry) -> dict:
        return _tutor_block(obj)

    def get_review(self, obj: Inquiry) -> dict:
        review = TutorReview.objects.filter(tutor=obj.tutor, author=obj.family).first()
        if not review:
            return {}
        return {
            "id": review.id,
            "rating": review.rating,
            "text": review.text,
        }



class TutorInquirySerializer(serializers.ModelSerializer):
    """
    Serializer for the tutor-side inquiry endpoints.

    Includes a nested `family` block with contact fields. In Phase 5 contact
    fields are always null regardless of contact_revealed value — the key shape
    is stable for the client.

    # TODO Phase 6: when contact_revealed=True, replace nulls with real values
    # from obj.family (full_name, phone, email).
    """

    tutor_id = serializers.IntegerField(source="tutor.id", read_only=True)
    family = serializers.SerializerMethodField()

    class Meta:
        model = Inquiry
        fields = [
            "id",
            "tutor_id",
            "family",
            "status",
            "message",
            "contact_revealed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

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
    """Input serializer for POST /api/v1/inquiries/.

    `tutor_id` is the id of the tutor's *user*. The view passes
    ``context={"request": request}`` so we can reject a family inquiring to
    their own tutor profile.
    """

    tutor_id = serializers.IntegerField()
    message = serializers.CharField(min_length=1)

    def validate_tutor_id(self, value: int) -> int:
        request = self.context.get("request")
        tutor_detail = get_object_or_404(TutorDetail, id=value)
        if request is not None and tutor_detail.user == request.user:
            raise serializers.ValidationError(
                "You cannot send an inquiry to your own tutor profile."
            )
        return value


class InquiryStatusUpdateSerializer(serializers.Serializer):
    """
    Input serializer for PATCH /api/v1/tutor/inquiries/{id}/.

    A tutor may move an inquiry into CONTACTED, ACCEPTED, DECLINED or COMPLETED.
    CANCELLED is family-only and NEW is the creation default, so neither is
    selectable here. The state machine in services.transition enforces which
    of these are legal from the inquiry's current status.
    """

    status = serializers.ChoiceField(
        choices=[
            (s, InquiryStatus(s).label) for s in sorted(TUTOR_SETTABLE_STATUSES)
        ]
    )
