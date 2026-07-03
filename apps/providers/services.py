from apps.users.models import Role
from apps.providers.models import ProviderChoices, TutorDetail, ProviderVerification, StatusChoices
import logging

logger = logging.getLogger(__name__)

def apply_verification_outcome(verification: ProviderVerification, reviewer = None) -> bool:
    approved = verification.status == StatusChoices.APPROVED
    user = verification.user

    role, _ = Role.objects.get_or_create(name=verification.provider_type)
    if approved:
        user.roles.add(role)
    else:
        user.roles.remove(role)
    if hasattr(user, "_role_names_cache"):
        del user._role_names_cache

        # Keep TutorDetail's mirror flag truthful for the tutor-detail API.
    if verification.provider_type == ProviderChoices.TUTOR:
        TutorDetail.objects.filter(
            user=user, deleted_at__isnull=True
        ).update(is_verified=approved)

    logger.info(
        "Reviewer %s set %s verification for %s to %s (role %s).",
        getattr(reviewer, "email", "system"),
        verification.provider_type,
        user.email,
        verification.status,
        "granted" if approved else "revoked",
    )

    # Fire-and-forget: notify the applicant of the outcome. Imported locally to
    # avoid an app-loading circular import; .delay() keeps the admin action from
    # blocking on (or breaking because of) push delivery.
    from apps.notifications.tasks import notify_verification_result

    notify_verification_result.delay(verification.id)

    return approved