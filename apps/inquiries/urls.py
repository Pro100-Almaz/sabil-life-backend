from rest_framework.routers import DefaultRouter

from apps.inquiries.views import FamilyInquiryViewSet, TutorInquiryViewSet

app_name = "inquiries"

# Family router — /api/v1/inquiries/
family_router = DefaultRouter()
family_router.register(r"inquiries", FamilyInquiryViewSet, basename="inquiries")

# Tutor router — /api/v1/tutor/inquiries/
tutor_router = DefaultRouter()
tutor_router.register(r"inquiries", TutorInquiryViewSet, basename="tutor-inquiries")

urlpatterns = family_router.urls

# Tutor URLs are mounted separately in conf/urls.py under "tutor/"
tutor_urlpatterns = tutor_router.urls
