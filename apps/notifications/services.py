import json
import logging

from django.conf import settings
from django.db import transaction
from firebase_admin import credentials, messaging, initialize_app

from apps.notifications.models import Device, Notification

logger = logging.getLogger(__name__)

_firebase_app = None


def _get_firebase_app():
    """Initialize and cache the Firebase app once (lazy singleton)."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    raw = settings.FIREBASE_CREDENTIALS
    if raw.strip().startswith("{"):
        cred = credentials.Certificate(json.loads(raw))  
    else:
        cred = credentials.Certificate(raw)  
    _firebase_app = initialize_app(cred)
    return _firebase_app


def send_push_to_user(user, title: str, body: str, data: dict) -> None:
    """
    Send an FCM push to all of a user's active devices
    """
    if not settings.PUSH_NOTIFICATIONS_ENABLED:
        logger.info("Push disabled; skipping FCM send for %s.", user.email)
        return

    tokens = list(
        Device.objects.filter(user=user, is_active=True).values_list(
            "fcm_token", flat=True
        )
    )
    if not tokens:
        return

    message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title=title, body=body),
        data={k: str(v) for k, v in data.items()},
    )
    response = messaging.send_each_for_multicast(message, app=_get_firebase_app())

    dead = []
    for token, resp in zip(tokens, response.responses):
        if resp.success:
            continue
        exc = resp.exception
        if isinstance(exc, messaging.UnregisteredError):
            dead.append(token)
        logger.warning("FCM send failed for token …%s: %s", token[-8:], exc)

    if dead:
        Device.objects.filter(fcm_token__in=dead).update(is_active=False)
        logger.info("Deactivated %d dead FCM token(s).", len(dead))


def notify_user(user, *, type: str, title: str, body: str, data: dict) -> Notification:
    """Persist an in-app notification AND send a push. Single entry point."""
    with transaction.atomic():
        notification = Notification.objects.create(
            user=user,
            type=type,
            title=title,
            body=body,
            data=data,
        )
    send_push_to_user(user, title, body, data)
    return notification
