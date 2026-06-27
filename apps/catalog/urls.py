from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.catalog.views import (
    ListingClientViewSet,
    ListingOwnerViewSet,
    ListingViewSet,
    TutorListViewSet,
    categories_view,
    tutor_subjects_view,
)

router = DefaultRouter()
router.register(r"listings", ListingViewSet, basename="listings")
router.register(r"tutors", TutorListViewSet, basename="tutors")
router.register(r"listing-enrollment", ListingClientViewSet, basename="listing-enrollment")
router.register(r"listing-clients", ListingOwnerViewSet, basename="listing-clients")

app_name = "catalog"

urlpatterns = router.urls + [
    path("categories/", categories_view, name="categories"),
    path("subjects/", tutor_subjects_view, name="subjects"),
]
