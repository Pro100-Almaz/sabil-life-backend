from rest_framework.routers import DefaultRouter

from apps.inquiries.views import FamilyInquiryViewSet, ProviderInquiryViewSet

app_name = "inquiries"

# Family router — /api/v1/inquiries/
family_router = DefaultRouter()
family_router.register(r"inquiries", FamilyInquiryViewSet, basename="inquiries")

# Provider router — /api/v1/provider/inquiries/
provider_router = DefaultRouter()
provider_router.register(
    r"inquiries", ProviderInquiryViewSet, basename="provider-inquiries"
)

urlpatterns = family_router.urls

# Provider URLs are mounted separately in conf/urls.py under "provider/"
provider_urlpatterns = provider_router.urls
