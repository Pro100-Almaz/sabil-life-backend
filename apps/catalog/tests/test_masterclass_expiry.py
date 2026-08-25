from datetime import timedelta

import pytest
from django.utils import timezone

from apps.catalog.models import (
    Listing,
    ListingCategory,
    ListingStatus,
    MasterclassEventType,
)
from apps.catalog.services import draft_expired_one_time_masterclasses


@pytest.mark.django_db
def test_expiry_check_drafts_only_expired_one_time_masterclasses(
    django_assert_num_queries,
):
    expired = Listing.objects.create(
        title="Expired event",
        category=ListingCategory.MASTERCLASSES,
        status=ListingStatus.ACTIVE,
        event_type=MasterclassEventType.ONE_TIME,
        starts_at=timezone.now() - timedelta(hours=2),
    )
    previous_updated_at = expired.updated_at
    within_grace_period = Listing.objects.create(
        title="Recently started event",
        category=ListingCategory.MASTERCLASSES,
        status=ListingStatus.ACTIVE,
        event_type=MasterclassEventType.ONE_TIME,
        starts_at=timezone.now() - timedelta(minutes=30),
    )
    ongoing = Listing.objects.create(
        title="Ongoing masterclass",
        category=ListingCategory.MASTERCLASSES,
        status=ListingStatus.ACTIVE,
        event_type=MasterclassEventType.ONGOING,
        starts_at=timezone.now() - timedelta(days=30),
    )

    with django_assert_num_queries(1):
        updated = draft_expired_one_time_masterclasses()

    expired.refresh_from_db()
    within_grace_period.refresh_from_db()
    ongoing.refresh_from_db()
    assert updated == 1
    assert expired.status == ListingStatus.DRAFT
    assert expired.updated_at > previous_updated_at
    assert within_grace_period.status == ListingStatus.ACTIVE
    assert ongoing.status == ListingStatus.ACTIVE
