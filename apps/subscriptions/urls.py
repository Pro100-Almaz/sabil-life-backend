from rest_framework.routers import DefaultRouter

from .views import FamilySubscriptionViewSet, ProviderSubscriptionViewSet

app_name = "subscriptions"

# Family router — /api/v1/subscriptions/
family_router = DefaultRouter()
family_router.register(
    r"subscriptions", FamilySubscriptionViewSet, basename="subscriptions"
)

# Provider router — /api/v1/provider/subscriptions/
provider_router = DefaultRouter()
provider_router.register(
    r"subscriptions", ProviderSubscriptionViewSet, basename="provider-subscriptions"
)

urlpatterns = family_router.urls
provider_urlpatterns = provider_router.urls
