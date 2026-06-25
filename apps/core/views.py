import mimetypes
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.throttling import AnonRateThrottle

from apps.core.tasks import test_task


class PingRateThrottle(AnonRateThrottle):
    rate = "10/minute"


@extend_schema(
    description="Handles a ping request to check if the server is responsive.",
    responses={
        200: {
            "type": "object",
            "properties": {"ping": {"type": "string"}},
            "example": {"ping": "pong"},
        },
        405: {
            "type": "object",
            "properties": {"detail": {"type": "string"}},
            "example": {"detail": 'Method "POST" not allowed.'},
        },
    },
)
@api_view(["GET"])
@throttle_classes([PingRateThrottle])
def ping(request):
    return JsonResponse({"ping": "pong"})


def _extract_storage_key(raw_url: str) -> str:
    parsed = urlparse(raw_url)
    bucket = getattr(settings, "AWS_STORAGE_BUCKET_NAME", "")
    path = unquote(parsed.path or "").lstrip("/")

    if not path:
        raise ValueError("Missing media path.")

    if bucket:
        bucket_prefix = f"{bucket}/"
        if path.startswith(bucket_prefix):
            path = path[len(bucket_prefix):]
        elif path == bucket:
            raise ValueError("Missing object key.")

    if not path or ".." in path.split("/"):
        raise ValueError("Invalid object key.")
    return path


@extend_schema(
    description=(
        "Retrieves a stored media object by a previously saved MinIO/media URL and "
        "streams the file through the API. Intended for clients that cannot "
        "reach the original MinIO host directly."
    ),
    parameters=[
        {
            "name": "url",
            "in": "query",
            "required": True,
            "schema": {"type": "string"},
            "description": "Previously saved media URL.",
        }
    ],
    responses={
        200: {"type": "string", "format": "binary"},
        400: {
            "type": "object",
            "properties": {"detail": {"type": "string"}},
            "example": {"detail": "Query parameter 'url' is required."},
        },
        404: {
            "type": "object",
            "properties": {"detail": {"type": "string"}},
            "example": {"detail": "Media file not found."},
        },
    },
)
@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def media_retrieve(request):
    raw_url = request.query_params.get("url", "").strip()
    if not raw_url:
        return JsonResponse({"detail": "Query parameter 'url' is required."}, status=400)

    try:
        storage_key = _extract_storage_key(raw_url)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    if not default_storage.exists(storage_key):
        raise Http404("Media file not found.")

    content_type, _ = mimetypes.guess_type(storage_key)
    response = FileResponse(
        default_storage.open(storage_key, "rb"),
        content_type=content_type or "application/octet-stream",
    )
    response["Cache-Control"] = "public, max-age=3600"
    return response


def fire_task(request):
    """
    TODO 🚫 After testing the view, remove it with the task and the route.

    Handles a request to fire a test Celery task. The task will be retried
    up to 3 times and after 5 seconds if it fails (by default). The retry
    time will be increased exponentially.
    """
    if request.method == "GET":
        test_task.delay()
        return JsonResponse({"task": "Task fired"})

    return JsonResponse({"error": "Method Not Allowed"}, status=405)
