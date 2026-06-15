from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import TestCase

from apps.providers.permissions import IsListingOwner, IsProvider
from apps.users.enums import UserRole


def _mock_request(user) -> MagicMock:
    req = MagicMock()
    req.user = user
    return req


def _mock_view() -> MagicMock:
    return MagicMock()


def _mock_user(role: str, authenticated: bool = True) -> SimpleNamespace:
    """
    Build a lightweight user-like object whose is_authenticated and is_provider
    can be freely set.  We use SimpleNamespace rather than a real CustomUser
    instance because AbstractUser.is_authenticated is a read-only property.
    """
    is_provider = role in {UserRole.TUTOR, UserRole.MASTERCLASS}
    return SimpleNamespace(
        is_authenticated=authenticated,
        is_provider=is_provider,
        role=role,
    )


class IsProviderTests(TestCase):
    def setUp(self):
        self.perm = IsProvider()
        self.view = _mock_view()

    def test_anonymous_user_denied(self):
        anon = _mock_user(UserRole.FAMILY, authenticated=False)
        req = _mock_request(anon)
        self.assertFalse(self.perm.has_permission(req, self.view))

    def test_family_denied(self):
        user = _mock_user(UserRole.FAMILY)
        req = _mock_request(user)
        self.assertFalse(self.perm.has_permission(req, self.view))

    def test_tutor_allowed(self):
        user = _mock_user(UserRole.TUTOR)
        req = _mock_request(user)
        self.assertTrue(self.perm.has_permission(req, self.view))

    def test_masterclass_allowed(self):
        user = _mock_user(UserRole.MASTERCLASS)
        req = _mock_request(user)
        self.assertTrue(self.perm.has_permission(req, self.view))

    def test_admin_denied(self):
        """
        ADMIN role returns False from IsProvider.
        Admins manage providers via /admin-panel/, not the provider self-service API.
        """
        user = _mock_user(UserRole.ADMIN)
        req = _mock_request(user)
        # ADMIN.is_provider is False (not in {TUTOR, MASTERCLASS})
        self.assertFalse(self.perm.has_permission(req, self.view))


class IsListingOwnerTests(TestCase):
    def setUp(self):
        self.perm = IsListingOwner()
        self.view = _mock_view()

    def test_owner_allowed(self):
        user = MagicMock()
        user.id = 42
        req = _mock_request(user)
        listing = MagicMock()
        listing.owner_id = 42
        self.assertTrue(self.perm.has_object_permission(req, self.view, listing))

    def test_non_owner_denied(self):
        user = MagicMock()
        user.id = 42
        req = _mock_request(user)
        listing = MagicMock()
        listing.owner_id = 99
        self.assertFalse(self.perm.has_object_permission(req, self.view, listing))
