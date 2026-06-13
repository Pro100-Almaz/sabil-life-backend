from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager


class UserRole(models.TextChoices):
    FAMILY = "FAMILY", _("Family")
    TUTOR = "TUTOR", _("Tutor")
    MASTERCLASS = "MASTERCLASS", _("Masterclass")
    ADMIN = "ADMIN", _("Admin")


class CustomUser(AbstractUser):
    """
    CustomUser is a custom user model that extends Django's AbstractUser.
    It uses email as the unique identifier instead of the username.
    """

    # The username field is set to None to disable it.
    username = None

    # The email field is set to be unique because it is the unique identifier.
    email = models.EmailField(_("email address"), unique=True)

    # Specifies the field to be used as the unique identifier for the user.
    USERNAME_FIELD = "email"

    # A list of fields that will be prompted for when creating a user
    # via the createsuperuser command. If empty, the USERNAME_FIELD is
    # the only required.
    REQUIRED_FIELDS = []

    # The CustomUserManager allows the creation of a user where email
    # is the unique identifier.
    objects = CustomUserManager()

    # Phase 1 fields
    full_name = models.CharField(_("full name"), max_length=255, blank=True, default="")
    role = models.CharField(
        _("role"),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.FAMILY,
    )
    phone = models.CharField(_("phone"), max_length=32, blank=True, default="")
    home_lat = models.FloatField(_("home latitude"), null=True, blank=True)
    home_lng = models.FloatField(_("home longitude"), null=True, blank=True)
    is_verified = models.BooleanField(
        _("verified"),
        default=False,
        help_text=_(
            "Providers must be verified by an admin before publishing listings. "
            "Families are verified on registration."
        ),
    )

    @property
    def is_provider(self) -> bool:
        """Return True if the user has a provider role (TUTOR or MASTERCLASS)."""
        return self.role in {UserRole.TUTOR, UserRole.MASTERCLASS}

    def __str__(self):
        return self.email
