from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Favorite


@admin.register(Favorite)
class FavoriteAdmin(ModelAdmin):
    list_display = ("listing", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("listing__title", "user__email")
    readonly_fields = ("id", "created_at")
    ordering = ("-created_at",)
