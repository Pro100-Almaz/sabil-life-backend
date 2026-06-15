from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.providers.models import ProviderProfile
from apps.users.enums import UserRole
from apps.users.models import CustomUser


def make_user(
    email: str,
    role: str = UserRole.TUTOR,
    verified: bool = True,
) -> CustomUser:
    return CustomUser.objects.create_user(
        email=email,
        password="TestPass123!",
        role=role,
        is_verified=verified,
    )


class ProviderProfileModelTests(TestCase):
    def test_is_verified_mirrors_user(self):
        user = make_user("tutor@example.com", verified=True)
        profile = ProviderProfile.objects.get_or_create_for_user(user)
        self.assertTrue(profile.is_verified)

        user.is_verified = False
        user.save()
        profile.refresh_from_db()
        self.assertFalse(profile.is_verified)

    def test_is_verified_false_for_unverified(self):
        user = make_user("unverified@example.com", verified=False)
        profile = ProviderProfile.objects.get_or_create_for_user(user)
        self.assertFalse(profile.is_verified)

    def test_clean_raises_for_family_role(self):
        user = make_user("family@example.com", role=UserRole.FAMILY)
        profile = ProviderProfile(user=user)
        with self.assertRaises(ValidationError) as ctx:
            profile.clean()
        self.assertEqual(ctx.exception.code, "invalid_role")

    def test_clean_raises_for_admin_role(self):
        user = make_user("admin@example.com", role=UserRole.ADMIN)
        profile = ProviderProfile(user=user)
        with self.assertRaises(ValidationError) as ctx:
            profile.clean()
        self.assertEqual(ctx.exception.code, "invalid_role")

    def test_clean_passes_for_tutor(self):
        user = make_user("tutor2@example.com", role=UserRole.TUTOR)
        profile = ProviderProfile(user=user)
        profile.clean()  # Should not raise

    def test_clean_passes_for_masterclass(self):
        user = make_user("mc@example.com", role=UserRole.MASTERCLASS)
        profile = ProviderProfile(user=user)
        profile.clean()  # Should not raise

    def test_save_calls_clean_and_rejects_family(self):
        user = make_user("family2@example.com", role=UserRole.FAMILY)
        profile = ProviderProfile(user=user)
        with self.assertRaises(ValidationError):
            profile.save()

    def test_get_or_create_for_user_idempotent(self):
        user = make_user("tutor3@example.com")
        profile1 = ProviderProfile.objects.get_or_create_for_user(user)
        profile2 = ProviderProfile.objects.get_or_create_for_user(user)
        self.assertEqual(profile1.pk, profile2.pk)

    def test_str_representation(self):
        user = make_user("tutor4@example.com")
        profile = ProviderProfile.objects.get_or_create_for_user(user)
        self.assertIn("tutor4@example.com", str(profile))

    def test_masterclass_profile_created(self):
        user = make_user("mc2@example.com", role=UserRole.MASTERCLASS)
        profile = ProviderProfile.objects.get_or_create_for_user(user)
        self.assertEqual(profile.user, user)

    def test_profile_fields_blank_by_default(self):
        user = make_user("blank@example.com")
        profile = ProviderProfile.objects.get_or_create_for_user(user)
        self.assertEqual(profile.display_name, "")
        self.assertEqual(profile.bio, "")
        self.assertEqual(profile.subjects, [])
        self.assertIsNone(profile.hourly_rate_qar)
        self.assertEqual(profile.availability, "")
