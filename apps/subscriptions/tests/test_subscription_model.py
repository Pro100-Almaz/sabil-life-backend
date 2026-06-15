"""
Tests for MasterclassSubscription model.

Covers: defaults, conditional unique constraint, __str__.
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.catalog.models import Listing, ListingCategory, ListingStatus
from apps.subscriptions.models import MasterclassSubscription, SubscriptionStatus
from apps.users.enums import UserRole

User = get_user_model()


def make_user(email, role=UserRole.FAMILY):
    return User.objects.create_user(email=email, password="pass1234!", role=role)


def make_listing(owner, category=ListingCategory.MASTERCLASSES):
    return Listing.objects.create(
        title="MC Listing", category=category, status=ListingStatus.ACTIVE, owner=owner
    )


def make_subscription(family, listing, provider, sub_status=SubscriptionStatus.CONFIRMED):
    return MasterclassSubscription.objects.create(
        family=family,
        listing=listing,
        provider=provider,
        status=sub_status,
    )


@pytest.mark.django_db
class TestMasterclassSubscriptionModel:
    def test_default_status_is_confirmed(self):
        family = make_user("fam_m@test.com")
        mc = make_user("mc_m@test.com", UserRole.MASTERCLASS)
        listing = make_listing(mc)
        sub = make_subscription(family, listing, mc)
        assert sub.status == SubscriptionStatus.CONFIRMED

    def test_cancelled_at_defaults_null(self):
        family = make_user("fam_m2@test.com")
        mc = make_user("mc_m2@test.com", UserRole.MASTERCLASS)
        listing = make_listing(mc)
        sub = make_subscription(family, listing, mc)
        assert sub.cancelled_at is None

    def test_str_representation(self):
        family = make_user("fam_m3@test.com")
        mc = make_user("mc_m3@test.com", UserRole.MASTERCLASS)
        listing = make_listing(mc)
        sub = make_subscription(family, listing, mc)
        assert str(sub) == f"Subscription {sub.id} ({sub.status})"

    def test_uuid_primary_key(self):
        import uuid

        family = make_user("fam_m4@test.com")
        mc = make_user("mc_m4@test.com", UserRole.MASTERCLASS)
        listing = make_listing(mc)
        sub = make_subscription(family, listing, mc)
        assert isinstance(sub.id, uuid.UUID)

    def test_ordering_most_recent_first(self):
        family = make_user("fam_m5@test.com")
        mc = make_user("mc_m5@test.com", UserRole.MASTERCLASS)
        listing = make_listing(mc)
        s1 = make_subscription(family, listing, mc)
        s2 = MasterclassSubscription.objects.create(
            family=family,
            listing=Listing.objects.create(
                title="Another MC",
                category=ListingCategory.MASTERCLASSES,
                status=ListingStatus.ACTIVE,
                owner=mc,
            ),
            provider=mc,
        )
        subs = list(MasterclassSubscription.objects.filter(family=family))
        assert subs[0].id == s2.id
        assert subs[1].id == s1.id

    def test_conditional_unique_constraint_blocks_second_confirmed(self):
        """Two CONFIRMED subscriptions for same (family, listing) raise IntegrityError."""
        family = make_user("fam_m6@test.com")
        mc = make_user("mc_m6@test.com", UserRole.MASTERCLASS)
        listing = make_listing(mc)
        make_subscription(family, listing, mc, SubscriptionStatus.CONFIRMED)
        with pytest.raises(IntegrityError):
            make_subscription(family, listing, mc, SubscriptionStatus.CONFIRMED)

    def test_two_cancelled_subscriptions_allowed(self):
        """Multiple CANCELLED rows for same (family, listing) are allowed."""
        family = make_user("fam_m7@test.com")
        mc = make_user("mc_m7@test.com", UserRole.MASTERCLASS)
        listing = make_listing(mc)
        make_subscription(family, listing, mc, SubscriptionStatus.CANCELLED)
        # Should not raise
        make_subscription(family, listing, mc, SubscriptionStatus.CANCELLED)
        assert (
            MasterclassSubscription.objects.filter(
                family=family, listing=listing, status=SubscriptionStatus.CANCELLED
            ).count()
            == 2
        )

    def test_confirmed_after_cancelled_allowed(self):
        """A new CONFIRMED subscription is allowed after an existing CANCELLED one."""
        family = make_user("fam_m8@test.com")
        mc = make_user("mc_m8@test.com", UserRole.MASTERCLASS)
        listing = make_listing(mc)
        make_subscription(family, listing, mc, SubscriptionStatus.CANCELLED)
        sub = make_subscription(family, listing, mc, SubscriptionStatus.CONFIRMED)
        assert sub.status == SubscriptionStatus.CONFIRMED
