from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.users.enums import UserRole
from apps.users.managers import CustomUserManager


class Role(models.Model):
    name = models.CharField(
        _("name"), max_length=20, choices=UserRole.choices, unique=True,
    )

    class Meta:
        verbose_name = _("role")
        verbose_name_plural = _("roles")

    def __str__(self) -> str:
        return self.name


class CustomUser(AbstractUser):
    username = None
    email = models.EmailField(_("email address"), unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    full_name = models.CharField(_("full name"), max_length=255, blank=True, default="")
    role = models.CharField(
        _("legacy role"),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.FAMILY,
    )
    roles = models.ManyToManyField(
        Role, related_name="users", blank=True, verbose_name=_("roles"),
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

    def _get_role_names(self) -> set[str]:
        if not hasattr(self, "_role_names_cache"):
            self._role_names_cache = set(
                self.roles.values_list("name", flat=True)
            )
        return self._role_names_cache

    def has_role(self, role_name: str) -> bool:
        role_names = self._get_role_names()
        if role_name in role_names:
            return True
        # MANAGER inherits every role except ADMIN
        if role_name != UserRole.ADMIN and UserRole.MANAGER in role_names:
            return True
        return False

    def has_any_role(self, *role_names: str) -> bool:
        return any(self.has_role(r) for r in role_names)

    @property
    def is_provider(self) -> bool:
        return self.has_any_role(UserRole.TUTOR, UserRole.MASTERCLASS)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Sync legacy role field → M2M for backward compatibility
        if self.role:
            role_obj, _ = Role.objects.get_or_create(name=self.role)
            self.roles.add(role_obj)
            if hasattr(self, "_role_names_cache"):
                del self._role_names_cache

    def __str__(self):
        return self.email
