from django.db import transaction
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver

from apps.catalog.models import Listing
from apps.catalog.services import url_to_storage_key
from apps.catalog.tasks import delete_storage_objects

def _enqueue_for_deletion(urls: list[str]) -> None: 
    keys = [k for u in (urls or []) if (k := url_to_storage_key(u))]
    if keys:
        transaction.on_commit(lambda: delete_storage_objects.delay(keys))

@receiver(pre_delete, sender= Listing)
def cleanup_images_on_delete(sender, instance: Listing, **kwargs) -> None: 
    """Listing row deleted -> delete all images from minio"""
    
    _enqueue_for_deletion(instance.image_urls)

@receiver(pre_save, sender=Listing)
def cleanup_images_on_update(sender, instance: Listing, **kwargs) -> None:
    """Listing row is updated -> delete removed images"""

    if instance._state.adding or instance.pk is None:
        return
    
    try: 
        old = sender.objects.get(pk = instance.pk)
    except sender.DoesNotExist:
        return
    
    removed = set(old.image_urls or []) - set (instance.image_urls or [])
    _enqueue_for_deletion(removed)
    