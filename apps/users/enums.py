from django.db import models
from django.utils.translation import gettext_lazy as _


class UserRole(models.TextChoices):
    FAMILY = "FAMILY", _("Family")
    TUTOR = "TUTOR", _("Tutor")
    MASTERCLASS = "MASTERCLASS", _("Masterclass")
    MANAGER = "MANAGER", _("Manager")
    ADMIN = "ADMIN", _("Admin")
