from django.urls import path
from knox import views as knox_views

from apps.users.views import CreateUserView, LoginView, RegisterView, UserMeView

app_name = "users"

urlpatterns = [
    # Admin-only user creation tool (existing, preserved)
    path("create/", CreateUserView.as_view(), name="create"),
    # Public self-service registration (Phase 1)
    path("register/", RegisterView.as_view(), name="register"),
    # Current-user profile — renamed from profile/ to me/ per spec §9
    path("me/", UserMeView.as_view(), name="me"),
    # Auth
    path("login/", LoginView.as_view(), name="knox_login"),
    path("logout/", knox_views.LogoutView.as_view(), name="knox_logout"),
    path("logoutall/", knox_views.LogoutAllView.as_view(), name="knox_logoutall"),
]
