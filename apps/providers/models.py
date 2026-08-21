import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ProviderChoices(models.TextChoices):
    MASTERCLASS = "MASTERCLASS", _("Masterclass")
    TUTOR = "TUTOR", _("Tutor")


class StatusChoices(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")
    UPDATED = "UPDATED", _("Updated")
    CANCELLED = "CANCELLED", _("Cancelled")


class TutorStatus(models.TextChoices):
    ACTIVE = "ACTIVE", _("Active")
    PAUSED = "PAUSED", _("Paused")
    DELETED = "DELETED", _("Deleted")


class AIScreeningStatus(models.TextChoices):
    QUEUED = "QUEUED", _("Queued")
    PROCESSING = "PROCESSING", _("Processing")
    RECOMMENDED = "RECOMMENDED", _("Recommended")
    NEEDS_REVIEW = "NEEDS_REVIEW", _("Needs review")
    INSUFFICIENT = "INSUFFICIENT", _("Insufficient information")
    FAILED = "FAILED", _("Failed")


class TutorDetailQuerySet(models.QuerySet):
    def with_subject(self, value: str) -> "TutorDetailQuerySet":
        return self.extra(
            where=[
                "EXISTS ("
                "SELECT 1 FROM jsonb_array_elements_text(subjects) AS elem "
                "WHERE lower(trim(elem)) = lower(trim(%s))"
                ")"
            ],
            params=[value],
        )


class TutorDetail(models.Model):
    objects = TutorDetailQuerySet.as_manager()
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tutor_detail",
        verbose_name=_("user"),
    )
    affiliation_listing_id = models.CharField(
        _("affiliation listing ID"),
        max_length=120,
        blank=True,
    )
    subjects = models.JSONField(
        _("subjects"),
        default=list,
        blank=True,
        help_text=_(
            'Free-text subject names, e.g. ["Chemistry", "Biology"]. '
            "Whitespace is trimmed automatically on save; matching against "
            "the subject filter is case/whitespace-insensitive."
        ),
    )
    formats = models.JSONField(
        _("formats"),
        default=list,
        blank=True,
        help_text=_('e.g. ["ONE_ON_ONE", "SMALL_GROUP", "AT_CENTRE"]'),
    )
    age_groups = models.JSONField(
        _("age groups"),
        default=list,
        blank=True,
        help_text=_('e.g. ["6-9", "10-12"]'),
    )
    price_per_hour_qar = models.PositiveIntegerField(
        _("price per hour (QAR)"),
        null=True,
        blank=True,
    )
    rating = models.DecimalField(
        _("rating"),
        max_digits=2,
        decimal_places=1,
        default=0,
    )
    review_count = models.PositiveIntegerField(_("review count"), default=0)
    years_experience = models.PositiveIntegerField(
        _("years of experience"),
        null=True,
        blank=True,
    )
    credentials = models.CharField(_("credentials"), max_length=300, blank=True)
    linkedin_url = models.URLField(_("LinkedIn URL"), max_length=500, blank=True)
    languages = models.JSONField(
        _("languages"),
        default=list,
        blank=True,
        help_text=_('e.g. ["EN", "AR"]'),
    )
    trial_available = models.BooleanField(_("trial available"), default=False)
    bio = models.TextField(_("bio"), blank=True)
    is_verified = models.BooleanField(_("verified"), default=False)
    deleted_at = models.DateTimeField(_("deleted at"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    city = models.CharField(_("city"), max_length=120, blank=True, null=True)
    availability = models.TextField(_("availability"), blank=True)
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=TutorStatus.choices,
        default=TutorStatus.ACTIVE,
    )

    class Meta:
        verbose_name = _("tutor detail")
        verbose_name_plural = _("tutor details")

    def clean(self) -> None:
        super().clean()
        if self.deleted_at:
            return

    def save(self, *args, **kwargs) -> None:
        self.clean()
        if isinstance(self.subjects, list):
            self.subjects = [
                s.strip() for s in self.subjects if isinstance(s, str) and s.strip()
            ]
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"TutorDetail({self.user.email})"


class TutorSubject(models.Model):
    name = models.CharField(_("name"), max_length=200, unique=True)

    class Meta:
        verbose_name = _("tutor subject")
        verbose_name_plural = _("tutor subjects")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class AvatarImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tutor = models.OneToOneField(
        TutorDetail,
        on_delete=models.CASCADE,
        related_name="avatar",
        verbose_name=_("tutor"),
    )
    key = models.CharField(max_length=512, unique=True)  # identity
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.key


class ProviderVerification(models.Model):
    """
    Tracks the verification lifecycle of a provider (TUTOR / MASTERCLASS).

    A record is created automatically when the provider first fills in their
    detail form (status=PENDING) and flips to UPDATED whenever they re-submit.
    A manager/admin then APPROVES or REJECTS it (with a comment on rejection),
    and the provider may CANCEL their own pending request.

    A user can have at most one verification per provider_type.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="provider_verifications",
        verbose_name=_("user"),
    )
    provider_type = models.CharField(
        _("provider type"),
        max_length=20,
        choices=ProviderChoices.choices,
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )
    comment = models.TextField(
        _("comment"),
        blank=True,
        help_text=_("Reviewer note — e.g. the reason a verification was rejected."),
    )
    cv = models.FileField(
        _("CV"),
        upload_to="provider-verifications/cvs/%Y/%m/",
        blank=True,
        help_text=_("Required PDF CV for masterclass provider applications."),
    )
    ai_processing_consent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("provider verification")
        verbose_name_plural = _("provider verifications")
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "provider_type"],
                name="unique_verification_per_user_provider_type",
            )
        ]

    def __str__(self) -> str:
        return (
            f"ProviderVerification({self.user.email}, {self.provider_type}, "
            f"{self.status})"
        )


class ProviderVerificationAIScreening(models.Model):
    """Advisory AI assessment; it never changes the verification decision."""

    verification = models.ForeignKey(
        ProviderVerification,
        on_delete=models.CASCADE,
        related_name="ai_screenings",
    )
    status = models.CharField(
        max_length=20,
        choices=AIScreeningStatus.choices,
        default=AIScreeningStatus.QUEUED,
    )
    summary = models.TextField(blank=True)
    strengths = models.JSONField(default=list, blank=True)
    concerns = models.JSONField(default=list, blank=True)
    missing_information = models.JSONField(default=list, blank=True)
    manual_checks = models.JSONField(default=list, blank=True)
    criteria = models.JSONField(default=list, blank=True)
    confidence = models.PositiveSmallIntegerField(null=True, blank=True)
    provider = models.CharField(max_length=40, default="openai")
    model = models.CharField(max_length=80, blank=True)
    rubric_version = models.CharField(max_length=20, default="1.0")
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("AI CV screening")
        verbose_name_plural = _("AI CV screenings")

    def __str__(self) -> str:
        return f"AI screening {self.pk} ({self.status})"
