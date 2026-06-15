from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ProviderListingViewSet, ProviderProfileView

app_name = "providers"

router = DefaultRouter()
# Only register routes we support (no PUT — handled via http_method_names on the view)
router.register(r"listings", ProviderListingViewSet, basename="provider-listings")

urlpatterns = [
    path("profile/", ProviderProfileView.as_view(), name="provider-profile"),
] + router.urls
