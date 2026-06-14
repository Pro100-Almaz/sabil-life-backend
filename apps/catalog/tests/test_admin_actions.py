"""
Tests for ListingAdmin bulk moderation actions — Phase 3.
"""

import pytest
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.catalog.admin import (
    ListingAdmin,
    approve_listings,
    mark_featured,
    reject_listings,
)
from apps.catalog.models import Listing, ListingCategory, ListingStatus

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def superuser(db):
    return User.objects.create_superuser(
        email="admin@example.com",
        password="adminpass123",
    )


@pytest.fixture()
def rf():
    return RequestFactory()


@pytest.fixture()
def admin_instance():
    return ListingAdmin(Listing, admin.site)


def _make_listing(**kwargs):
    defaults = {
        "title": "Test Listing",
        "category": ListingCategory.TUTORING,
        "status": ListingStatus.PENDING,
        "owner": None,
    }
    defaults.update(kwargs)
    return Listing.objects.create(**defaults)


def _request(rf, superuser):
    """Build a fake POST request with the superuser attached."""
    request = rf.post("/admin/")
    request.user = superuser
    # Django's message framework requires session + _messages on the request.
    from django.contrib.messages.storage.fallback import FallbackStorage

    request.session = {}  # type: ignore[attr-defined]
    request._messages = FallbackStorage(request)  # type: ignore[attr-defined]
    return request


# ---------------------------------------------------------------------------
# approve_listings
# ---------------------------------------------------------------------------


class TestApproveListings:
    def test_pending_becomes_active(self, rf, superuser, admin_instance):
        listing = _make_listing(status=ListingStatus.PENDING)
        qs = Listing.objects.filter(id=listing.id)
        approve_listings(admin_instance, _request(rf, superuser), qs)
        listing.refresh_from_db()
        assert listing.status == ListingStatus.ACTIVE

    def test_draft_becomes_active(self, rf, superuser, admin_instance):
        listing = _make_listing(status=ListingStatus.DRAFT)
        qs = Listing.objects.filter(id=listing.id)
        approve_listings(admin_instance, _request(rf, superuser), qs)
        listing.refresh_from_db()
        assert listing.status == ListingStatus.ACTIVE

    def test_rejected_is_skipped(self, rf, superuser, admin_instance):
        listing = _make_listing(status=ListingStatus.REJECTED)
        qs = Listing.objects.filter(id=listing.id)
        approve_listings(admin_instance, _request(rf, superuser), qs)
        listing.refresh_from_db()
        assert listing.status == ListingStatus.REJECTED  # unchanged

    def test_bulk_approve_only_eligible(self, rf, superuser, admin_instance):
        pending = _make_listing(status=ListingStatus.PENDING, title="Pending")
        rejected = _make_listing(status=ListingStatus.REJECTED, title="Rejected")
        qs = Listing.objects.filter(id__in=[pending.id, rejected.id])
        approve_listings(admin_instance, _request(rf, superuser), qs)
        pending.refresh_from_db()
        rejected.refresh_from_db()
        assert pending.status == ListingStatus.ACTIVE
        assert rejected.status == ListingStatus.REJECTED


# ---------------------------------------------------------------------------
# reject_listings
# ---------------------------------------------------------------------------


class TestRejectListings:
    def test_pending_becomes_rejected(self, rf, superuser, admin_instance):
        listing = _make_listing(status=ListingStatus.PENDING)
        qs = Listing.objects.filter(id=listing.id)
        reject_listings(admin_instance, _request(rf, superuser), qs)
        listing.refresh_from_db()
        assert listing.status == ListingStatus.REJECTED

    def test_active_becomes_rejected(self, rf, superuser, admin_instance):
        listing = _make_listing(status=ListingStatus.ACTIVE)
        qs = Listing.objects.filter(id=listing.id)
        reject_listings(admin_instance, _request(rf, superuser), qs)
        listing.refresh_from_db()
        assert listing.status == ListingStatus.REJECTED

    def test_already_rejected_unchanged(self, rf, superuser, admin_instance):
        listing = _make_listing(status=ListingStatus.REJECTED)
        qs = Listing.objects.filter(id=listing.id)
        reject_listings(admin_instance, _request(rf, superuser), qs)
        listing.refresh_from_db()
        assert listing.status == ListingStatus.REJECTED


# ---------------------------------------------------------------------------
# mark_featured
# ---------------------------------------------------------------------------


class TestMarkFeatured:
    def test_sets_is_featured_true(self, rf, superuser, admin_instance):
        listing = _make_listing(is_featured=False)
        qs = Listing.objects.filter(id=listing.id)
        mark_featured(admin_instance, _request(rf, superuser), qs)
        listing.refresh_from_db()
        assert listing.is_featured is True

    def test_idempotent_on_already_featured(self, rf, superuser, admin_instance):
        listing = _make_listing(is_featured=True)
        qs = Listing.objects.filter(id=listing.id)
        mark_featured(admin_instance, _request(rf, superuser), qs)
        listing.refresh_from_db()
        assert listing.is_featured is True


# ---------------------------------------------------------------------------
# Actions registered on ListingAdmin
# ---------------------------------------------------------------------------


class TestAdminActionsRegistered:
    def test_all_four_actions_registered(self, admin_instance):
        action_names = [
            a.__name__ if callable(a) else a
            for a in admin_instance.actions
        ]
        assert "approve_listings" in action_names
        assert "reject_listings" in action_names
        assert "mark_featured" in action_names
        assert "unmark_featured" in action_names
