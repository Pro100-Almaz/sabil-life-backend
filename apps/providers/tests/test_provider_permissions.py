from types import SimpleNamespace
from unittest.mock import MagicMock

from django.test import TestCase

from apps.providers.permissions import IsListingOwner
from apps.users.enums import UserRole
from apps.users.permissions import IsProvider



def _mock_request(user) -> MagicMock:
    req = MagicMock()
    req.user = user
    return req


def _mock_view() -> MagicMock:
    return MagicMock()


def _mock_user(role: str, authenticated: bool = True) -> SimpleNamespace:
    is_provider = role in {UserRole.TUTOR, UserRole.MASTERCLASS}
    role_set = {role}

    def has_role(r):
        if r in role_set:
            return True
        if r != UserRole.ADMIN and UserRole.MANAGER in role_set:
            return True
        return False

    def has_any_role(*roles):
        return any(has_role(r) for r in roles)

    return SimpleNamespace(
        is_authenticated=authenticated,
        is_provider=is_provider,
        role=role,
        has_role=has_role,
        has_any_role=has_any_role,
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
        user = _mock_user(UserRole.ADMIN)
        req = _mock_request(user)
        self.assertFalse(self.perm.has_permission(req, self.view))

    def test_manager_allowed(self):
        user = _mock_user(UserRole.MANAGER)
        req = _mock_request(user)
        self.assertTrue(self.perm.has_permission(req, self.view))


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
