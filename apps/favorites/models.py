"""
Favorites model

One favorite per (listing, user) pair, enforced via UniqueConstraint.

"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import Listing

class Favorite(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="favorite",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta: 
        constraints = [
            models.UniqueConstraint(
                fields=["user", "listing"],
                name = "unique_user_favorite_listing"
            ) 
        ]

    def __str__ (self):
        return Favorite(listing = self.listing, user = self.user)