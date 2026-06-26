from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.catalog.models import ListingImage
from apps.catalog.tasks import delete_storage_objects

@receiver(post_delete, sender=ListingImage)
def cleanup_image_object(sender, instance, **kwargs):
    transaction.on_commit(lambda: delete_storage_objects.delay([instance.key]))