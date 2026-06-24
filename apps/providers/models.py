from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.users.enums import UserRole


class ProviderProfileManager(models.Manager):
    """Custom manager with a lazy-create helper."""

    def get_or_create_for_user(self, user) -> "ProviderProfile":
        """
        Return the ProviderProfile for *user*, creating it if it doesn't exist.

        This is the canonical lazy-create entry point used by the profile view.
        It avoids the complexity of post_save signals while guaranteeing a
        freshly-registered TUTOR/MASTERCLASS always gets a 200 on first GET,
        rather than a 404.
        """
        profile, _ = self.get_or_create(user=user)
        return profile


class ProviderProfile(models.Model):
    """
    One-to-one profile record for provider users (TUTOR or MASTERCLASS role).

    is_verified is a read-through property that mirrors user.is_verified so
    there is a single source of truth — the admin flips the flag on CustomUser,
    not here.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="provider_profile",
        verbose_name=_("user"),
    )
    display_name = models.CharField(_("display name"), max_length=200, blank=True)
    bio = models.TextField(_("bio"), blank=True)
    subjects = models.JSONField(
        _("subjects"),
        default=list,
        blank=True,
        help_text=_('List of subject strings, e.g. ["Math", "Arabic"].'),
    )
    hourly_rate_qar = models.PositiveIntegerField(
        _("hourly rate (QAR)"), null=True, blank=True
    )
    availability = models.TextField(_("availability"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProviderProfileManager()

    class Meta:
        verbose_name = _("provider profile")
        verbose_name_plural = _("provider profiles")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def clean(self) -> None:
        """Reject profiles for non-provider users."""
        super().clean()
        if self.user_id and self.user.role not in {UserRole.TUTOR, UserRole.MASTERCLASS}:
            raise ValidationError(
                _(
                    "ProviderProfile can only be created for users with role "
                    "TUTOR or MASTERCLASS. Current role: %(role)s."
                ),
                params={"role": self.user.role},
                code="invalid_role",
            )

    def save(self, *args, **kwargs) -> None:
        self.clean()
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_verified(self) -> bool:
        """Read-through: mirrors user.is_verified — single source of truth."""
        return self.user.is_verified

    def __str__(self) -> str:
        return f"ProviderProfile({self.user.email})"


class TutorDetail(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tutor_detail",
        verbose_name=_("user"),
    )
    avatar = models.ImageField(
        _("avatar"), upload_to="avatars/", blank=True,
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("tutor detail")
        verbose_name_plural = _("tutor details")

    def clean(self) -> None:
        super().clean()
        if self.user_id and self.user.role != UserRole.TUTOR:
            raise ValidationError(
                _("TutorDetail can only be created for users with role TUTOR."),
                code="invalid_role",
            )

    def save(self, *args, **kwargs) -> None:
        self.clean()
        if self.pk:
            try:
                old = TutorDetail.objects.get(pk=self.pk)
            except TutorDetail.DoesNotExist:
                old = None
            if old and old.avatar and old.avatar != self.avatar:
                old.avatar.delete(save=False)
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
