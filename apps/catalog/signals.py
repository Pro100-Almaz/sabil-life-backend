from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.catalog.models import Event, ListingStatus
from apps.notifications.tasks import notify_provider_event


@receiver(post_save, sender=Event, dispatch_uid="notify_provider_event_published")
def event_published(sender, instance, created, raw=False, **kwargs):
    listing = instance.listing
    if (
        created
        and not raw
        and listing.owner_id
        # Don't push followers to a listing they can't open in the catalog.
        and listing.status == ListingStatus.ACTIVE
    ):
        # Capture the publisher: a later ownership transfer must not notify
        # followers of the new owner about an older publication.
        event_id = str(instance.pk)
        provider_id = listing.owner_id
        transaction.on_commit(
            lambda: notify_provider_event.delay(event_id, provider_id), robust=True
        )
