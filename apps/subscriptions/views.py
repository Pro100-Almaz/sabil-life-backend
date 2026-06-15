"""
Subscription views — Phase 5 MASTERCLASSES auto-confirm flow.

Family endpoints:
  GET/POST /api/v1/subscriptions/        — list own / create
  GET      /api/v1/subscriptions/{id}/   — detail (includes private listing fields)
  DELETE   /api/v1/subscriptions/{id}/   — cancel (soft: status=CANCELLED)

Provider endpoints:
  GET  /api/v1/provider/subscriptions/            — list received (?status=, ?listing_id=)
  GET  /api/v1/provider/subscriptions/{id}/       — detail
"""

import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response

from apps.catalog.models import Listing
from apps.providers.permissions import IsProvider

from . import services
from .models import MasterclassSubscription, SubscriptionStatus
from .permissions import IsFamily
from .schema import (
    PROVIDER_SUBSCRIPTION_LIST_SCHEMA,
    PROVIDER_SUBSCRIPTION_RETRIEVE_SCHEMA,
    SUBSCRIPTION_CANCEL_SCHEMA,
    SUBSCRIPTION_CREATE_SCHEMA,
    SUBSCRIPTION_LIST_SCHEMA,
    SUBSCRIPTION_RETRIEVE_SCHEMA,
)
from .serializers import (
    FamilySubscriptionSerializer,
    ProviderSubscriptionSerializer,
    SubscriptionCreateSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Family ViewSet
# ---------------------------------------------------------------------------


@extend_schema_view(
    list=extend_schema(**SUBSCRIPTION_LIST_SCHEMA),
    create=extend_schema(**SUBSCRIPTION_CREATE_SCHEMA),
    retrieve=extend_schema(**SUBSCRIPTION_RETRIEVE_SCHEMA),
    destroy=extend_schema(**SUBSCRIPTION_CANCEL_SCHEMA),
)
class FamilySubscriptionViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Family-side subscription endpoints.

    list     — GET    /api/v1/subscriptions/       — own subscriptions (paginated).
    create   — POST   /api/v1/subscriptions/       — subscribe to MASTERCLASSES listing.
    retrieve — GET    /api/v1/subscriptions/{id}/  — detail with private listing fields.
    destroy  — DELETE /api/v1/subscriptions/{id}/  — cancel (soft delete).

    Cancellation: sets status=CANCELLED + cancelled_at=now(). The row is
    retained for audit purposes. The family may re-subscribe after cancellation
    because the conditional UniqueConstraint only blocks duplicate CONFIRMED rows.
    """

    permission_classes = [permissions.IsAuthenticated, IsFamily]
    lookup_field = "id"

    def get_queryset(self):
        qs = MasterclassSubscription.objects.filter(
            family=self.request.user
        ).select_related("listing", "provider")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return SubscriptionCreateSerializer
        return FamilySubscriptionSerializer

    def create(self, request, *args, **kwargs):
        input_serializer = SubscriptionCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        listing_id = input_serializer.validated_data["listing_id"]
        listing = get_object_or_404(Listing, pk=listing_id)

        try:
            subscription = services.create_subscription(
                family=request.user,
                listing=listing,
            )
        except services.DuplicateSubscription as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        out_serializer = FamilySubscriptionSerializer(
            subscription, context={"request": request}
        )
        logger.info(
            "Family %s subscribed to listing %s (subscription %s).",
            request.user.email,
            listing_id,
            subscription.id,
        )
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        subscription = get_object_or_404(
            MasterclassSubscription,
            id=kwargs["id"],
            family=request.user,
        )
        serializer = FamilySubscriptionSerializer(
            subscription, context={"request": request}
        )
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Soft-cancel the subscription.

        Sets status=CANCELLED and cancelled_at=now(). The row is kept for
        audit. The family may create a new subscription for the same listing
        after cancellation (the conditional unique constraint permits this).
        """
        subscription = get_object_or_404(
            MasterclassSubscription,
            id=kwargs["id"],
            family=request.user,
        )
        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = timezone.now()
        subscription.save(update_fields=["status", "cancelled_at", "updated_at"])
        logger.info(
            "Family %s cancelled subscription %s.",
            request.user.email,
            subscription.id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Provider ViewSet
# ---------------------------------------------------------------------------


@extend_schema_view(
    list=extend_schema(**PROVIDER_SUBSCRIPTION_LIST_SCHEMA),
    retrieve=extend_schema(**PROVIDER_SUBSCRIPTION_RETRIEVE_SCHEMA),
)
class ProviderSubscriptionViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Provider-side subscription endpoints.

    list     — GET /api/v1/provider/subscriptions/      — roster of subscribers.
    retrieve — GET /api/v1/provider/subscriptions/{id}/ — detail.

    Filterable by ?status= and ?listing_id=.
    Provider sees family id and full_name; contact details deferred to Phase 6.
    """

    serializer_class = ProviderSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated, IsProvider]
    lookup_field = "id"

    def get_queryset(self):
        qs = MasterclassSubscription.objects.filter(
            provider=self.request.user
        ).select_related("family", "listing")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        listing_id = self.request.query_params.get("listing_id")
        if listing_id:
            qs = qs.filter(listing_id=listing_id)
        return qs

    def retrieve(self, request, *args, **kwargs):
        subscription = get_object_or_404(
            MasterclassSubscription,
            id=kwargs["id"],
            provider=request.user,
        )
        serializer = ProviderSubscriptionSerializer(
            subscription, context={"request": request}
        )
        return Response(serializer.data)
