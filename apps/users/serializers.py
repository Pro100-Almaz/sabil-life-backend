import logging
from typing import cast

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.users.enums import UserRole
from apps.users.models import CustomUser

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
    Public self-service registration.

    Every user registers as FAMILY.  Additional roles (TUTOR, MASTERCLASS,
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

    def create(self, validated_data: dict) -> CustomUser:
        from apps.users.models import Role

        validated_data["is_verified"] = True
        user = CustomUser.objects.create_user(**validated_data)
        family_role, _ = Role.objects.get_or_create(name=UserRole.FAMILY)
        user.roles.add(family_role)
        return user


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
            "password",
        )
        extra_kwargs = {
            "id": {"read_only": True},
            "email": {"read_only": True},
            "is_verified": {"read_only": True},
            "password": {"write_only": True, "min_length": MIN_PASSWORD_LENGTH},
        }

    def get_roles(self, obj: CustomUser) -> list[str]:
        return list(obj.roles.values_list("name", flat=True))

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