from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.providers.follows import ProviderFollowViewSet, ProviderSubscriberViewSet
from apps.providers.views import (
    AvatarUploadView,
    ListingImageDetailView,
    ListingImageView,
    ListingOwnershipAdminViewSet,
    ListingOwnershipRequestViewSet,
    ProviderEventViewSet,
    ProviderListingViewSet,
    ProviderProfileView,
    ProviderVerificationAdminViewSet,
    TutorDetailView,
    VerifyProviderView,
)

app_name = "providers"

router = DefaultRouter()
router.register("subscribers", ProviderSubscriberViewSet, basename="provider-subscribers")
# Only register routes we support (no PUT — handled via http_method_names on the view)
router.register(r"listings", ProviderListingViewSet, basename="provider-listings")
router.register(
    r"ownership-requests/admin",
    ListingOwnershipAdminViewSet,
    basename="ownership-admin",
)
router.register(
    r"ownership-requests",
    ListingOwnershipRequestViewSet,
    basename="ownership-requests",
)
router.register(
    r"verify/admin",
    ProviderVerificationAdminViewSet,
    basename="provider-verify-admin",
)

urlpatterns = router.urls + [
    path(
        "listings/<uuid:listing_id>/events/",
        ProviderEventViewSet.as_view({"get": "list", "post": "create"}),
        name="provider-listing-events",
    ),
    path(
        "listings/<uuid:listing_id>/events/<uuid:pk>/",
        ProviderEventViewSet.as_view(
            {
                "get": "retrieve",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="provider-listing-event-detail",
    ),
    # router.urls first so "verify/admin/" is matched by the admin viewset
    # before the catch-all "verify/<provider_type>/" below can swallow it.
    path("verify/", VerifyProviderView.as_view(), name="provider-verify"),
    path("profile/", ProviderProfileView.as_view(), name="provider-profile"),
    path(
        "verify/<str:provider_type>/",
        VerifyProviderView.as_view(),
        name="provider-verify-cancel",
    ),
    path("tutor-detail/", TutorDetailView.as_view(), name="tutor-detail"),
    path("avatar/", AvatarUploadView.as_view(), name="avatar-upload"),
    path(
        "listings/<uuid:listing_id>/images/",
        ListingImageView.as_view(),
        name="listing-images",
    ),
    path(
        "listings/<uuid:listing_id>/images/<uuid:image_id>/",
        ListingImageDetailView.as_view(),
        name="listing-image-detail",
    ),
]

follow_router = DefaultRouter()
follow_router.register(
    "provider-subscriptions", ProviderFollowViewSet, basename="provider-follows"
)
follow_urlpatterns = follow_router.urls
