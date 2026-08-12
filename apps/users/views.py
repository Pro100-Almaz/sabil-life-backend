import logging
from datetime import datetime
from datetime import timezone as tz

from django.contrib.auth import login
from django.db import IntegrityError, transaction
from drf_spectacular.utils import extend_schema, extend_schema_view
from knox.auth import TokenAuthentication
from knox.models import AuthToken
from knox.settings import knox_settings
from knox.views import LoginView as KnoxLoginView
from rest_framework import generics, permissions, serializers, status, throttling
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.users import otp
from apps.users.enums import UserRole
from apps.users.models import CustomUser, Role
from apps.users.schema import (
    LOGIN_RESPONSE_SCHEMA,
    PROFILE_DETAIL_SCHEMA,
    PROFILE_PATCH_SCHEMA,
    PROFILE_PUT_SCHEMA,
    REGISTER_REQUEST_RESPONSE_SCHEMA,
    REGISTER_RESPONSE_SCHEMA,
    USER_CREATE_RESPONSE_SCHEMA,
)
from apps.users.serializers import (
    AuthTokenSerializer,
    CreateUserSerializer,
    ForgotPasswordConfirmSerializer,
    ForgotPasswordRequestSerializer,
    RegistrationRequestSerializer,
    RegistrationVerifySerializer,
    UserProfileSerializer,
)
from apps.users.tasks import send_password_reset_email, send_verification_email
from apps.users.throttles import (
    PasswordResetRequestThrottle,
    RegistrationCodeThrottle,
    UserLoginRateThrottle,
)

logger = logging.getLogger(__name__)


class ForgotPasswordView(generics.GenericAPIView):
    """
    Request a password-reset code.

    The response never reveals whether the submitted email belongs to an
    account.
    """

    permission_classes = (permissions.AllowAny,)
    serializer_class = ForgotPasswordRequestSerializer
    throttle_classes = [PasswordResetRequestThrottle]

    def post(self, request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        user = CustomUser.objects.filter(
            email__iexact=email,
            is_active=True,
        ).first()

        if user is not None:
            code = otp.start_password_reset(email=user.email)
            send_password_reset_email.delay(user.email, code)

        return Response(
            {
                "detail": (
                    "If an account exists for this email, a reset code has been sent."
                )
            },
            status=status.HTTP_200_OK,
        )


class ForgotPasswordConfirmView(generics.GenericAPIView):
    """
    Verify a password-reset code and set a new password.

    A successful reset invalidates every existing Knox token for the user.
    """

    permission_classes = (permissions.AllowAny,)
    serializer_class = ForgotPasswordConfirmSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset_confirm"

    _ERROR_MESSAGES = {
        "expired": "Code expired or not found. Please request a new one.",
        "invalid": "Invalid code.",
        "too_many_attempts": "Too many attempts. Please request a new code.",
    }

    def post(self, request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]
        new_password = serializer.validated_data["password"]

        user = CustomUser.objects.filter(
            email__iexact=email,
            is_active=True,
        ).first()

        if user is None:
            raise serializers.ValidationError(
                {"code": ["Code expired or not found. Please request a new one."]}
            )

        try:
            otp.verify_password_reset_code(
                email=user.email,
                code=code,
            )
        except otp.VerificationError as exc:
            message = self._ERROR_MESSAGES.get(exc.reason, "Invalid code.")
            raise serializers.ValidationError({"code": [message]}) from exc

        with transaction.atomic():
            user.set_password(new_password)
            user.save(update_fields=["password"])

            # A stolen or previously issued session must not survive a reset.
            AuthToken.objects.filter(user=user).delete()

        logger.info("Password reset completed for user ID %s.", user.pk)

        return Response(
            {"detail": "Password reset successfully."},
            status=status.HTTP_200_OK,
        )


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
    request=RegistrationRequestSerializer,
    responses=REGISTER_REQUEST_RESPONSE_SCHEMA,
)
class RegisterView(generics.GenericAPIView):
    """
    Step 1 of public self-service registration.

    Validates the inputs (email not taken, password strong), generates a
    verification code, and emails it. **No account is created here** — the
    account is created only once the code is verified via /register/verify/.

    Response shape: {detail}  (200 OK; nothing sensitive is returned)
    """

    permission_classes = (permissions.AllowAny,)
    serializer_class = RegistrationRequestSerializer
    throttle_classes = [RegistrationCodeThrottle]

    def post(self, request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            logger.warning("Registration request failed: %s", e.detail)
            raise

        data = serializer.validated_data
        code = otp.start_pending_registration(
            email=data["email"],
            password=data["password"],
            full_name=data.get("full_name", ""),
            phone=data.get("phone", ""),
        )
        send_verification_email.delay(data["email"], code)
        logger.info("Verification code requested for %s", data["email"])
        return Response(
            {"detail": "Verification code sent."},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    request=RegistrationVerifySerializer,
    responses=REGISTER_RESPONSE_SCHEMA,
)
class RegisterVerifyView(generics.GenericAPIView):
    """
    Step 2 of public self-service registration.

    Verifies the emailed code and, on success, creates the account with
    is_verified=True and returns a Knox bearer token (the user is logged in
    immediately — no separate login step needed).

    Response shape: {user, token, expiry}
    """

    permission_classes = (permissions.AllowAny,)
    serializer_class = RegistrationVerifySerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register_verify"

    _ERROR_MESSAGES = {
        "expired": "Code expired or not found. Please request a new one.",
        "invalid": "Invalid code.",
        "too_many_attempts": "Too many attempts. Please request a new code.",
    }

    def post(self, request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        try:
            pending = otp.verify_and_pop(email=email, code=code)
        except otp.VerificationError as e:
            message = self._ERROR_MESSAGES.get(e.reason, "Invalid code.")
            raise serializers.ValidationError({"code": [message]}) from e

        try:
            user = self._create_user(email, pending)
        except IntegrityError as e:
            raise serializers.ValidationError(
                {"email": ["A user with this email already exists."]}
            ) from e

        _, token = AuthToken.objects.create(user)
        token_ttl = knox_settings.TOKEN_TTL
        expiry = datetime.now(tz=tz.utc) + token_ttl if token_ttl is not None else None

        logger.info("User %s registered (email verified).", user.email)

        user_data = UserProfileSerializer(user, context={"request": request}).data
        return Response(
            {"user": user_data, "token": token, "expiry": expiry},
            status=status.HTTP_201_CREATED,
        )

    def _create_user(self, email: str, pending: dict) -> CustomUser:
        user = CustomUser(
            email=CustomUser.objects.normalize_email(email),
            full_name=pending["full_name"],
            phone=pending["phone"],
            is_verified=True,
        )
        # The pending password is already hashed — assign directly rather than
        # set_password(), which would double-hash it and break login.
        user.password = pending["password"]
        user.save()
        family_role, _created = Role.objects.get_or_create(name=UserRole.FAMILY)
        user.roles.add(family_role)
        return user


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
