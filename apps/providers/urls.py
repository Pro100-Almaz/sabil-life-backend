from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AvatarUploadView, ProviderListingViewSet, ProviderProfileView, TutorDetailView

app_name = "providers"

router = DefaultRouter()
# Only register routes we support (no PUT — handled via http_method_names on the view)
router.register(r"listings", ProviderListingViewSet, basename="provider-listings")

urlpatterns = [
    path("profile/", ProviderProfileView.as_view(), name="provider-profile"),
    path("tutor-detail/", TutorDetailView.as_view(), name="tutor-detail"),
    path("avatar/", AvatarUploadView.as_view(), name="avatar-upload"),
] + router.urls
