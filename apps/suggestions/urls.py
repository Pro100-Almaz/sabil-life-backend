from rest_framework.routers import DefaultRouter

from .views import FamilySuggestionViewSet

app_name = "suggestions"

router = DefaultRouter()
router.register(r"suggestions", FamilySuggestionViewSet, basename="suggestions")

urlpatterns = router.urls
