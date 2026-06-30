from celery import shared_task
from django.core.files.storage import default_storage

from apps.core.tasks import BaseTaskWithRetry


@shared_task(bind=True, base=BaseTaskWithRetry)
def delete_storage_objects(self, keys: list[str]) -> None:
    """Delete a batch of storage objects by key. Retries on failure (3x, backoff)."""
    for key in keys:
        if key:
            default_storage.delete(key)