from rest_framework.routers import DefaultRouter

from apps.notifications.views import DeviceViewSet, NotificationViewSet

app_name = "notifications"

router = DefaultRouter()
router.register(r"notifications/devices", DeviceViewSet, basename="devices")
router.register(r"notifications", NotificationViewSet, basename="notifications")

urlpatterns = router.urls
