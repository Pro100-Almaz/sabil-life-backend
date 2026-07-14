import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.users.enums import UserRole


class ProviderChoices(models.TextChoices):
    MASTERCLASS = "MASTERCLASS", _("Masterclass")
    TUTOR = "TUTOR", _("Tutor")


class StatusChoices(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")
    UPDATED = "UPDATED", _("Updated")
    CANCELLED = "CANCELLED", _("Cancelled")



class TutorDetail(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tutor_detail",
        verbose_name=_("user"),
    )
    affiliation_listing_id = models.CharField(
        _("affiliation listing ID"), max_length=120, blank=True,
    )
    subjects = models.JSONField(_("subjects"), default=list, blank=True)
    formats = models.JSONField(
        _("formats"), default=list, blank=True,
        help_text=_('e.g. ["ONE_ON_ONE", "SMALL_GROUP", "AT_CENTRE"]'),
    )
    age_groups = models.JSONField(
        _("age groups"), default=list, blank=True,
        help_text=_('e.g. ["6-11", "12-15"]'),
    )
    price_per_hour_qar = models.PositiveIntegerField(
        _("price per hour (QAR)"), null=True, blank=True,
    )
    rating = models.DecimalField(
        _("rating"), max_digits=2, decimal_places=1, default=0,
    )
    review_count = models.PositiveIntegerField(_("review count"), default=0)
    years_experience = models.PositiveIntegerField(
        _("years of experience"), null=True, blank=True,
    )
    credentials = models.CharField(_("credentials"), max_length=300, blank=True)
    languages = models.JSONField(
        _("languages"), default=list, blank=True,
        help_text=_('e.g. ["EN", "AR"]'),
    )
    trial_available = models.BooleanField(_("trial available"), default=False)
    bio = models.TextField(_("bio"), blank=True)
    is_verified = models.BooleanField(_("verified"), default=False)
    deleted_at = models.DateTimeField(_("deleted at"), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    city = models.CharField(_("city"), max_length=120, blank=True, null=True)

    class Meta:
        verbose_name = _("tutor detail")
        verbose_name_plural = _("tutor details")

    def clean(self) -> None:
        super().clean()
        if self.deleted_at:
            return

    def save(self, *args, **kwargs) -> None:
        self.clean()
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
        verbose_name=_("tutor")
    )
    key = models.CharField(max_length=512, unique=True) #identity 
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
        return f"ProviderVerification({self.user.email}, {self.provider_type}, {self.status})"
