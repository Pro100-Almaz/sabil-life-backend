from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.catalog.views import ListingViewSet, TutorListViewSet, categories_view, tutor_subjects_view

router = DefaultRouter()
router.register(r"listings", ListingViewSet, basename="listings")
router.register(r"tutors", TutorListViewSet, basename="tutors")

app_name = "catalog"

urlpatterns = router.urls + [
    path("categories/", categories_view, name="categories"),
    path("subjects/", tutor_subjects_view, name="subjects"),
]
