from django.urls import path
from knox import views as knox_views

from apps.users.views import (
    CreateUserView,
    ForgotPasswordConfirmView,
    ForgotPasswordView,
    LoginView,
    RegisterVerifyView,
    RegisterView,
    UserMeView,
)

app_name = "users"

urlpatterns = [
    # Admin-only user creation tool (existing, preserved)
    path("create/", CreateUserView.as_view(), name="create"),
    # Public self-service registration — two-step email verification.
    # Step 1: request a code. Step 2: verify the code and create the account.
    path("register/", RegisterView.as_view(), name="register"),
    path("register/verify/", RegisterVerifyView.as_view(), name="register-verify"),
    # Current-user profile — renamed from profile/ to me/ per spec §9
    path("me/", UserMeView.as_view(), name="me"),
    # Auth
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot-password"),
    path("forgot-password/confirm/", ForgotPasswordConfirmView.as_view(), name="forgot-password-confirm"),
    path("login/", LoginView.as_view(), name="knox_login"),
    path("logout/", knox_views.LogoutView.as_view(), name="knox_logout"),
    path("logoutall/", knox_views.LogoutAllView.as_view(), name="knox_logoutall"),
]
