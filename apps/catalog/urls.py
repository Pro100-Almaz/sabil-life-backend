from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ListingViewSet, categories_view

router = DefaultRouter()
router.register(r"listings", ListingViewSet, basename="listings")

app_name = "catalog"

urlpatterns = router.urls + [
    path("categories/", categories_view, name="categories"),
]
