"""
Inquiry service layer — state machine lives here, not in views.

All business logic for creating and transitioning inquiries is centralised so
that views stay thin and the transitions are easy to unit-test in isolation.
"""

from django.conf import settings

from apps.providers.models import TutorDetail

from apps.inquiries.models import Inquiry, InquiryStatus
from apps.notifications.tasks import notify_inquiry_result
# Statuses a TUTOR is allowed to move an inquiry into.
TUTOR_SETTABLE_STATUSES: frozenset[str] = frozenset(
    {
        InquiryStatus.CONTACTED,
        InquiryStatus.ACCEPTED,
        InquiryStatus.DECLINED,
        InquiryStatus.COMPLETED,
    }
)


class InvalidTransition(Exception):
    """Raised when an inquiry transition is not permitted by the state machine."""


# ---------------------------------------------------------------------------
# Valid transitions: {current_status: frozenset of allowed next statuses}
# ---------------------------------------------------------------------------
_ALLOWED: dict[str, frozenset[str]] = {
    InquiryStatus.NEW: frozenset(
        {
            InquiryStatus.CONTACTED,
            InquiryStatus.ACCEPTED,
            InquiryStatus.DECLINED,
            InquiryStatus.CANCELLED,
        }
    ),
    InquiryStatus.CONTACTED: frozenset(
        {InquiryStatus.ACCEPTED, InquiryStatus.DECLINED, InquiryStatus.CANCELLED}
    ),
    InquiryStatus.ACCEPTED: frozenset({InquiryStatus.COMPLETED}),
    InquiryStatus.DECLINED: frozenset(),
    InquiryStatus.COMPLETED: frozenset(),
    InquiryStatus.CANCELLED: frozenset(),
}


def create_inquiry(family, tutor: TutorDetail, message: str) -> Inquiry:
    """
    Create a new Inquiry addressed to a tutor.

    Validates:
    - tutor profile is not soft-deleted.

    No duplicate-prevention: families may re-inquire after a DECLINED or
    CANCELLED inquiry.
    """
    if tutor.deleted_at is not None:
        raise ValueError("This tutor is no longer available.")
    
    inquiry = Inquiry.objects.create(
        family=family,
        tutor=tutor,
        message=message,
        status=InquiryStatus.NEW,
    )

    notify_inquiry_result.delay(inquiry.id)

    return inquiry


def transition(inquiry: Inquiry, action: str, *, actor) -> Inquiry:
    """
    Transition an inquiry to a new status via a named action.

    action is the target status string (e.g. "CONTACTED", "ACCEPTED").
    actor is the user performing the transition (used for future audit logging).

    Raises InvalidTransition if the transition is not permitted.
    """
    allowed = _ALLOWED.get(inquiry.status, frozenset())
    if action not in allowed:
        raise InvalidTransition(
            f"Cannot transition inquiry from {inquiry.status!r} to {action!r}. "
            f"Allowed next statuses: {sorted(allowed) or 'none (terminal state)'}."
        )
    inquiry.status = action
    inquiry.save(update_fields=["status", "updated_at"])
    # Phase 6 stopgap: auto-reveal contact on accept when billing gate is off.
    # When BILLING_GATE_ENABLED=True (production with billing live) this block
    # is skipped and billing.services.on_inquiry_accepted() handles reveal.
    # See docs/PHASE_6_BILLING.md.
    if action == InquiryStatus.ACCEPTED and not settings.BILLING_GATE_ENABLED:
        inquiry.contact_revealed = True
        inquiry.save(update_fields=["contact_revealed", "updated_at"])

    notify_inquiry_result.delay(inquiry.id)
    return inquiry
