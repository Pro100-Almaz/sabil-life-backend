from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.providers.views import (
    AvatarUploadView,
    ProviderListingViewSet,
    ProviderVerificationAdminViewSet,
    TutorDetailView,
    VerifyProviderView,
    ListingImageDetailView,
    ListingImageView
)

app_name = "providers"

router = DefaultRouter()
# Only register routes we support (no PUT — handled via http_method_names on the view)
router.register(r"listings", ProviderListingViewSet, basename="provider-listings")
router.register(
    r"verify/admin",
    ProviderVerificationAdminViewSet,
    basename="provider-verify-admin",
)

urlpatterns = router.urls + [
    # router.urls first so "verify/admin/" is matched by the admin viewset
    # before the catch-all "verify/<provider_type>/" below can swallow it.
    path("verify/", VerifyProviderView.as_view(), name="provider-verify"),
    path(
        "verify/<str:provider_type>/",
        VerifyProviderView.as_view(),
        name="provider-verify-cancel",
    ),
    path("tutor-detail/", TutorDetailView.as_view(), name="tutor-detail"),
    path("avatar/", AvatarUploadView.as_view(), name="avatar-upload"),
    path("listings/<uuid:listing_id>/images/",
        ListingImageView.as_view(), name="listing-images"),
    path("listings/<uuid:listing_id>/images/<uuid:image_id>/",
        ListingImageDetailView.as_view(), name="listing-image-detail"),
]
