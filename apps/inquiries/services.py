"""
Inquiry service layer — state machine lives here, not in views.

All business logic for creating and transitioning inquiries is centralised so
that views stay thin and the transitions are easy to unit-test in isolation.
"""

from django.conf import settings

from apps.catalog.models import Listing, ListingCategory, ListingStatus

from .models import Inquiry, InquiryStatus


class InvalidTransition(Exception):
    """Raised when an inquiry transition is not permitted by the state machine."""


# ---------------------------------------------------------------------------
# Valid transitions: {current_status: frozenset of allowed next statuses}
# ---------------------------------------------------------------------------
_ALLOWED: dict[str, frozenset[str]] = {
    InquiryStatus.NEW: frozenset(
        {InquiryStatus.CONTACTED, InquiryStatus.ACCEPTED, InquiryStatus.DECLINED}
    ),
    InquiryStatus.CONTACTED: frozenset({InquiryStatus.ACCEPTED, InquiryStatus.DECLINED}),
    InquiryStatus.ACCEPTED: frozenset({InquiryStatus.COMPLETED}),
    InquiryStatus.DECLINED: frozenset(),
    InquiryStatus.COMPLETED: frozenset(),
}


def create_inquiry(family, listing: Listing, message: str) -> Inquiry:
    """
    Create a new Inquiry for a TUTORING listing.

    Validates:
    - listing is ACTIVE
    - listing category is TUTORING

    Snapshots provider = listing.owner at creation time.
    No duplicate-prevention: families may re-inquire after a DECLINED inquiry.
    """
    if listing.status != ListingStatus.ACTIVE:
        raise ValueError("Listing is not active.")
    if listing.category != ListingCategory.TUTORING:
        raise ValueError(
            "Inquiries only allowed on TUTORING listings; "
            "use /subscriptions/ for masterclasses."
        )
    if listing.owner_id is None:
        raise ValueError(
            "Listing has no provider assigned and cannot accept inquiries."
        )
    return Inquiry.objects.create(
        family=family,
        listing=listing,
        provider=listing.owner,
        message=message,
        status=InquiryStatus.NEW,
    )


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
    return inquiry
