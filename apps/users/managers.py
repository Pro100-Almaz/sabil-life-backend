from typing import TYPE_CHECKING

from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _

from apps.users.enums import UserRole

if TYPE_CHECKING:
    from apps.users.models import CustomUser


class CustomUserManager(BaseUserManager):
    def create_user(
        self, email: str, password: str, **extra_fields: dict
    ) -> "CustomUser":
        if not email:
            raise ValueError(_("The Email must be set"))

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: str, **extra_fields: dict
    ) -> "CustomUser":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", UserRole.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        user = self.create_user(email, password, **extra_fields)

        from apps.users.models import Role

        admin_role, _created = Role.objects.get_or_create(name=UserRole.ADMIN)
        user.roles.add(admin_role)
        return user
