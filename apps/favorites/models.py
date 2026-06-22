"""
Review model — Phase 7.

One review per (listing, author) pair, enforced via UniqueConstraint.
Reviews drive the denormalized rating/review_count on Listing via a
post_save/post_delete signal (see signals.py).

No TimeStampedModel mixin exists in this codebase yet — Phases 1-5
added created_at/updated_at inline everywhere. We continue that pattern.
"""

import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Favorites(models.Model):
    listing = models.ForeignKey(
        "catalog.Listing",
        on_delete=models.PROTECT,
        related_name="favorites",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="favorited_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    models.UniqueConstraint(fields=["user", "listing"])

    def __str__ (self):
        return