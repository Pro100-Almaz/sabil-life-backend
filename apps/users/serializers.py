import logging
from typing import cast

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.users.models import CustomUser
from apps.users.otp import CODE_LENGTH
from apps.users.utils import get_errors

logger = logging.getLogger(__name__)
MIN_PASSWORD_LENGTH = getattr(settings, "MIN_PASSWORD_LENGTH", 8)


class AuthTokenSerializer(serializers.Serializer):
    email = serializers.EmailField(label=_("Email"), write_only=True)
    password = serializers.CharField(
        label=_("Password"),
        style={"input_type": "password"},
        trim_whitespace=False,
        write_only=True,
    )
    token = serializers.CharField(label=_("Token"), read_only=True)

    def validate(self, attrs: dict) -> dict:
        email = attrs.get("email")
        password = attrs.get("password")

        # The authenticate call simply returns None for is_active=False users
        if email and password:
            user = cast(
                CustomUser | None,
                authenticate(
                    request=self.context.get("request"), email=email, password=password
                ),
            )

            if not user:
                msg = _("Unable to log in with provided credentials.")
                logger.warning("Failed login attempt for email: %s", email)
                raise serializers.ValidationError(msg, code="authorization")
        else:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg, code="authorization")

        attrs["user"] = user
        return attrs


class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=MIN_PASSWORD_LENGTH)
    password2 = serializers.CharField(write_only=True, min_length=MIN_PASSWORD_LENGTH)

    class Meta:
        model = CustomUser
        fields = ("email", "password", "password2")

    def validate(self, data: dict) -> dict:
        password = data["password"]

        # Check password match
        if password != data["password2"]:
            raise serializers.ValidationError("Passwords do not match.")

        user_data = {k: v for k, v in data.items() if k != "password2"}
        try:
            validate_password(password, self.Meta.model(**user_data))
        except Exception as e:
            if hasattr(e, "error_list"):
                errors = get_errors(e)
            else:
                errors = [
                    _("An error occurred during password validation. Please try again.")
                ]
            raise serializers.ValidationError({"password": errors}) from e

        return data

    def create(self, validated_data: dict) -> CustomUser:
        validated_data.pop("password2")
        return CustomUser.objects.create_user(**validated_data)


class RegistrationRequestSerializer(serializers.ModelSerializer):
    """
    Step 1 of self-service registration: validate the inputs before a
    verification code is emailed. Deliberately does NOT create anything —
    the account is only created once the code is verified (step 2).

    Every user registers as FAMILY. Additional roles (TUTOR, MASTERCLASS,
    MANAGER) are granted later by a manager/admin after verification.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=MIN_PASSWORD_LENGTH,
        style={"input_type": "password"},
    )
    full_name = serializers.CharField(required=False, allow_blank=True, default="")
    phone = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = CustomUser
        fields = ("email", "password", "full_name", "phone")

    def validate_email(self, value: str) -> str:
        # Fail fast: surface a taken email BEFORE we email a code.
        if CustomUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(_("A user with this email already exists."))
        return value

    def validate(self, data: dict) -> dict:
        password = data.get("password", "")
        user_data = {k: v for k, v in data.items() if k != "password"}
        try:
            validate_password(password, self.Meta.model(**user_data))
        except Exception as e:
            if hasattr(e, "error_list"):
                errors = get_errors(e)
            else:
                errors = [
                    _("An error occurred during password validation. Please try again.")
                ]
            raise serializers.ValidationError({"password": errors}) from e
        return data


class RegistrationVerifySerializer(serializers.Serializer):
    """Step 2: the email plus the code emailed to it."""

    email = serializers.EmailField()
    code = serializers.CharField(min_length=CODE_LENGTH, max_length=CODE_LENGTH)


class ForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ForgotPasswordConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(
        min_length=CODE_LENGTH,
        max_length=CODE_LENGTH,
        trim_whitespace=True,
    )
    password = serializers.CharField(
        write_only=True,
        min_length=MIN_PASSWORD_LENGTH,
        trim_whitespace=False,
        style={"input_type": "password"},
    )
    password2 = serializers.CharField(
        write_only=True,
        min_length=MIN_PASSWORD_LENGTH,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    def validate(self, data: dict) -> dict:
        password = data["password"]

        if password != data["password2"]:
            raise serializers.ValidationError(
                {"password2": [_("Passwords do not match.")]}
            )

        # Validate consistently without exposing whether the account exists.
        validation_user = CustomUser(email=data["email"])

        try:
            validate_password(password, user=validation_user)
        except Exception as exc:
            if hasattr(exc, "error_list"):
                errors = get_errors(exc)
            else:
                errors = [
                    _("An error occurred during password validation. Please try again.")
                ]

            raise serializers.ValidationError({"password": errors}) from exc

        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=MIN_PASSWORD_LENGTH,
        trim_whitespace=False,
        style={"input_type": "password"},
    )
    new_password2 = serializers.CharField(
        write_only=True,
        min_length=MIN_PASSWORD_LENGTH,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    def validate_old_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError(_("Current password is incorrect."))
        return value

    def validate(self, data: dict) -> dict:
        user = self.context["request"].user
        new_password = data["new_password"]

        if new_password != data["new_password2"]:
            raise serializers.ValidationError(
                {"new_password2": [_("Passwords do not match.")]}
            )

        if user.check_password(new_password):
            raise serializers.ValidationError(
                {"new_password": [_("New password must differ from current password.")]}
            )

        try:
            validate_password(new_password, user=user)
        except Exception as exc:
            if hasattr(exc, "error_list"):
                errors = get_errors(exc)
            else:
                errors = [
                    _("An error occurred during password validation. Please try again.")
                ]
            raise serializers.ValidationError({"new_password": errors}) from exc

        return data


class UserProfileSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "email",
            "full_name",
            "roles",
            "is_verified",
            "phone",
            "home_lat",
            "home_lng",
            "first_name",
            "last_name",
        )
        extra_kwargs = {
            "id": {"read_only": True},
            "email": {"read_only": True},
            "is_verified": {"read_only": True},
        }

    def get_roles(self, obj: CustomUser) -> list[str]:
        return list(obj.roles.values_list("name", flat=True))


class LoginResponseSerializer(serializers.Serializer):
    expiry = serializers.DateTimeField()
    token = serializers.CharField()
    user = UserProfileSerializer()


class RegisterResponseSerializer(serializers.Serializer):
    """Schema-only serializer describing the register endpoint response shape."""

    token = serializers.CharField()
    expiry = serializers.DateTimeField()
    user = UserProfileSerializer()
