import logging
from datetime import datetime
from datetime import timezone as tz

from django.contrib.auth import login
from drf_spectacular.utils import extend_schema, extend_schema_view
from knox.auth import TokenAuthentication
from knox.models import AuthToken
from knox.settings import knox_settings
from knox.views import LoginView as KnoxLoginView
from rest_framework import generics, permissions, serializers, status, throttling
from rest_framework.response import Response

from .schema import (
    LOGIN_RESPONSE_SCHEMA,
    PROFILE_DETAIL_SCHEMA,
    PROFILE_PATCH_SCHEMA,
    PROFILE_PUT_SCHEMA,
    REGISTER_RESPONSE_SCHEMA,
    USER_CREATE_RESPONSE_SCHEMA,
)
from .serializers import (
    AuthTokenSerializer,
    CreateUserSerializer,
    RegisterSerializer,
    UserProfileSerializer,
)
from .throttles import UserLoginRateThrottle

logger = logging.getLogger(__name__)


@extend_schema(responses=LOGIN_RESPONSE_SCHEMA)
class LoginView(KnoxLoginView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (permissions.AllowAny,)
    serializer_class = AuthTokenSerializer
    throttle_classes = [UserLoginRateThrottle]

    def post(self, request, format=None) -> Response:
        serializer = AuthTokenSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        login(request, user)
        logger.info("User %s logged in.", user.email)
        return super(LoginView, self).post(request, format=None)


@extend_schema(
    request=RegisterSerializer,
    responses=REGISTER_RESPONSE_SCHEMA,
)
class RegisterView(generics.CreateAPIView):
    """
    Public self-service registration endpoint.

    Creates a new user account and returns a Knox bearer token immediately
    (the user is logged in on registration — no separate login step needed).

    Role rules:
    - Default role is FAMILY.
    - TUTOR and MASTERCLASS users are created with is_verified=False; an admin
      must verify them before their listings become visible.
    - ADMIN role is rejected — admins are created via createsuperuser or the
      Django admin /create/ endpoint.

    Response shape: {user, token, expiry}  (Knox single-token, not JWT access+refresh)
    """

    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer
    throttle_classes = [throttling.AnonRateThrottle]

    def create(self, request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            logger.warning("Registration failed: %s", e.detail)
            raise

        user = serializer.save()
        _, token = AuthToken.objects.create(user)
        token_ttl = knox_settings.TOKEN_TTL
        expiry = datetime.now(tz=tz.utc) + token_ttl if token_ttl is not None else None

        logger.info("User %s registered.", user.email)

        user_data = UserProfileSerializer(user, context={"request": request}).data
        return Response(
            {"user": user_data, "token": token, "expiry": expiry},
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(responses=PROFILE_DETAIL_SCHEMA),
    patch=extend_schema(responses=PROFILE_PATCH_SCHEMA),
    put=extend_schema(responses=PROFILE_PUT_SCHEMA),
)
class UserMeView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH/PUT the currently authenticated user's profile.

    Replaces the old /profile/ endpoint. The URL name is 'me'.
    """

    serializer_class = UserProfileSerializer
    permission_classes = (permissions.IsAuthenticated,)
    throttle_classes = [throttling.UserRateThrottle]

    def get_object(self):
        return self.request.user


@extend_schema(responses=USER_CREATE_RESPONSE_SCHEMA)
class CreateUserView(generics.CreateAPIView):
    permission_classes = (permissions.IsAdminUser,)
    serializer_class = CreateUserSerializer
    throttle_classes = [throttling.UserRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            logger.info("User %s created.", serializer.data["email"])
            return Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )
        except serializers.ValidationError as e:
            logger.warning("Failed to create user: %s", e.detail)
            raise

    def perform_create(self, serializer):
        serializer.save()
