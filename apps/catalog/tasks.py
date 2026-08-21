from datetime import timedelta

from celery import shared_task
from django.core.files.storage import default_storage
from django.utils import timezone

from apps.catalog.models import (
    Listing,
    ListingCategory,
    ListingStatus,
    MasterclassEventType,
)
from apps.core.tasks import BaseTaskWithRetry


@shared_task(bind=True, base=BaseTaskWithRetry)
def delete_storage_objects(self, keys: list[str]) -> None:
    """Delete a batch of storage objects by key. Retries on failure (3x, backoff)."""
    for key in keys:
        if key:
            default_storage.delete(key)


@shared_task
def archive_expired_one_time_masterclasses() -> int:
    """Move one-time masterclasses to draft one hour after their start time."""
    cutoff = timezone.now() - timedelta(hours=1)
    return Listing.objects.filter(
        category=ListingCategory.MASTERCLASSES,
        event_type=MasterclassEventType.ONE_TIME,
        starts_at__lte=cutoff,
        status__in=[ListingStatus.ACTIVE, ListingStatus.PENDING],
    ).update(status=ListingStatus.DRAFT, updated_at=timezone.now())
