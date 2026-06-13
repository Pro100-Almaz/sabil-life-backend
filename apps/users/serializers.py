import logging
from typing import cast

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import CustomUser, UserRole
from .utils import get_errors

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


class RegisterSerializer(serializers.ModelSerializer):
    """
    Public self-service registration serializer.

    Differences from CreateUserSerializer (admin tool):
    - Exposes full_name, role, phone
    - Rejects role=ADMIN (admins created via Django admin / createsuperuser)
    - Sets is_verified=True for FAMILY, False for TUTOR/MASTERCLASS
    - No password2 confirm field — single password field with full validation
    """

    password = serializers.CharField(
        write_only=True,
        min_length=MIN_PASSWORD_LENGTH,
        style={"input_type": "password"},
    )
    role = serializers.ChoiceField(
        choices=UserRole.choices,
        default=UserRole.FAMILY,
        required=False,
    )
    full_name = serializers.CharField(required=False, allow_blank=True, default="")
    phone = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = CustomUser
        fields = ("email", "password", "full_name", "role", "phone")

    def validate_role(self, value: str) -> str:
        if value == UserRole.ADMIN:
            raise serializers.ValidationError(
                _("Cannot self-register with the ADMIN role.")
            )
        return value

    def validate(self, data: dict) -> dict:
        password = data.get("password", "")
        # Build a throwaway model instance for similarity validation
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

    def create(self, validated_data: dict) -> CustomUser:
        role = validated_data.get("role", UserRole.FAMILY)
        # Families are verified on registration; providers need admin verification.
        is_verified = role not in {UserRole.TUTOR, UserRole.MASTERCLASS}
        validated_data["is_verified"] = is_verified
        return CustomUser.objects.create_user(**validated_data)


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the /me/ endpoint. Exposes all Phase 1 profile fields.
    Password is write-only (used for password-change on PATCH/PUT).
    """

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "email",
            "full_name",
            "role",
            "is_verified",
            "phone",
            "home_lat",
            "home_lng",
            "first_name",
            "last_name",
            "password",
        )
        extra_kwargs = {
            "id": {"read_only": True},
            "email": {"read_only": True},
            "role": {"read_only": True},
            "is_verified": {"read_only": True},
            "password": {"write_only": True, "min_length": MIN_PASSWORD_LENGTH},
        }

    def validate(self, data: dict) -> dict:
        if "password" in data:
            try:
                user = self.instance if self.instance else self.Meta.model(**data)
                validate_password(data["password"], user=user)
            except Exception as e:
                if hasattr(e, "error_list"):
                    errors = get_errors(e)
                else:
                    errors = ["Password validation error. Please try again."]

                raise serializers.ValidationError({"password": errors}) from e

        return data

    def update(self, instance: CustomUser, validated_data: dict) -> CustomUser:
        password = validated_data.pop("password", None)
        user: CustomUser = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()

        return user


class LoginResponseSerializer(serializers.Serializer):
    expiry = serializers.DateTimeField()
    token = serializers.CharField()
    user = UserProfileSerializer()


class RegisterResponseSerializer(serializers.Serializer):
    """Schema-only serializer describing the register endpoint response shape."""

    token = serializers.CharField()
    expiry = serializers.DateTimeField()
    user = UserProfileSerializer()
