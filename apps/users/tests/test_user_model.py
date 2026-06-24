import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.users.enums import UserRole


@pytest.mark.django_db
class TestUserModel:
    @pytest.fixture
    def user(self):
        User = get_user_model()
        return User.objects.create_user(email="test@example.com", password="testpass123")

    def test_create_user(self, user):
        assert user.email == "test@example.com"
        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser
        assert user.username is None
        assert user.check_password("testpass123")

    def test_create_user_gets_family_role(self, user):
        assert user.has_role(UserRole.FAMILY)

    def test_create_user_empty_email(self):
        User = get_user_model()
        with pytest.raises(ValueError, match="The Email must be set"):
            User.objects.create_user(email="", password="foo")

    def test_email_normalization(self):
        User = get_user_model()
        email = "Test@Example.COM"
        user = User.objects.create_user(email=email, password="foo")
        assert user.email == "Test@example.com"

    def test_email_uniqueness(self, user):
        User = get_user_model()
        with pytest.raises(IntegrityError):
            User.objects.create_user(email="test@example.com", password="anotherpass")

    def test_string_representation(self, user):
        assert str(user) == user.email

    def test_create_superuser(self):
        User = get_user_model()
        admin_user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass"
        )
        assert admin_user.email == "admin@example.com"
        assert admin_user.is_active
        assert admin_user.is_staff
        assert admin_user.is_superuser
        assert admin_user.check_password("adminpass")
        assert admin_user.has_role(UserRole.ADMIN)

    def test_create_superuser_invalid_flags(self):
        User = get_user_model()
        with pytest.raises(ValueError):
            User.objects.create_superuser(
                email="admin@example.com", password="adminpass", is_staff=False
            )
        with pytest.raises(ValueError):
            User.objects.create_superuser(
                email="admin@example.com", password="adminpass", is_superuser=False
            )

    def test_user_required_fields(self):
        User = get_user_model()
        assert User.REQUIRED_FIELDS == []
        assert User.USERNAME_FIELD == "email"

    def test_has_role_with_m2m(self):
        from apps.users.models import Role

        User = get_user_model()
        user = User.objects.create_user(email="roles@example.com", password="testpass123")
        tutor_role, _ = Role.objects.get_or_create(name=UserRole.TUTOR)
        user.roles.add(tutor_role)
        # Refetch to clear any cached state
        user = User.objects.get(pk=user.pk)
        assert user.has_role(UserRole.TUTOR)
        assert user.has_role(UserRole.FAMILY)
        assert not user.has_role(UserRole.ADMIN)

    def test_manager_inherits_all_except_admin(self):
        from apps.users.models import Role

        User = get_user_model()
        user = User.objects.create_user(
            email="manager@example.com", password="testpass123", role=UserRole.MANAGER,
        )
        assert user.has_role(UserRole.FAMILY)
        assert user.has_role(UserRole.TUTOR)
        assert user.has_role(UserRole.MASTERCLASS)
        assert user.has_role(UserRole.MANAGER)
        assert not user.has_role(UserRole.ADMIN)
        assert user.is_provider
