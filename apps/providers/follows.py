"""Free provider subscriptions, separate from paid listing subscriptions."""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.providers.models import ProviderFollow
from apps.users.enums import UserRole
from apps.users.models import CustomUser
from apps.users.permissions import IsFamily, IsProvider


class ProviderFollowSerializer(serializers.ModelSerializer):
    provider_id = serializers.UUIDField(source="provider.uuid", read_only=True)
    display_name = serializers.CharField(source="provider.full_name", read_only=True)

    class Meta:
        model = ProviderFollow
        fields = ["provider_id", "display_name"]


class ProviderFollowCreateSerializer(serializers.Serializer):
    provider_id = serializers.UUIDField()


class ProviderSubscriberSerializer(serializers.ModelSerializer):
    client_id = serializers.UUIDField(source="client.uuid", read_only=True)
    full_name = serializers.CharField(source="client.full_name", read_only=True)

    class Meta:
        model = ProviderFollow
        fields = ["id", "client_id", "full_name", "created_at"]
        read_only_fields = fields


class SubscriberCountSerializer(serializers.Serializer):
    count = serializers.IntegerField(read_only=True)


@extend_schema_view(
    list=extend_schema(operation_id="v1_provider_follows_list"),
    destroy=extend_schema(operation_id="v1_provider_follows_destroy"),
)
class ProviderFollowViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Clients manage their own follows using the provider's public UUID."""

    permission_classes = [permissions.IsAuthenticated, IsFamily]
    serializer_class = ProviderFollowSerializer
    queryset = ProviderFollow.objects.none()
    lookup_field = "provider__uuid"
    lookup_url_kwarg = "provider_id"
    lookup_value_regex = (
        "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    )
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return ProviderFollowCreateSerializer
        return ProviderFollowSerializer

    def get_queryset(self):
        return ProviderFollow.objects.filter(client=self.request.user).select_related(
            "provider"
        )

    @extend_schema(
        operation_id="v1_provider_follows_create",
        request=ProviderFollowCreateSerializer,
        responses={200: ProviderFollowSerializer, 201: ProviderFollowSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = get_object_or_404(
            CustomUser.objects.filter(
                is_active=True,
                deleted_at__isnull=True,
                roles__name__in=[UserRole.TUTOR, UserRole.MASTERCLASS],
            ).distinct(),
            uuid=serializer.validated_data["provider_id"],
        )
        if provider.pk == request.user.pk:
            raise serializers.ValidationError(
                {"provider_id": "You cannot subscribe to yourself."}
            )
        follow, created = ProviderFollow.objects.get_or_create(
            client=request.user, provider=provider
        )
        return Response(
            ProviderFollowSerializer(follow).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ProviderSubscriberViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Subscriber identities and timestamps are visible only to their provider."""

    permission_classes = [permissions.IsAuthenticated, IsProvider]
    serializer_class = ProviderSubscriberSerializer
    queryset = ProviderFollow.objects.none()
    http_method_names = ["get", "head", "options"]

    def get_queryset(self):
        # Never accept a provider ID from the caller, even for managers/admins.
        return ProviderFollow.objects.filter(provider=self.request.user).select_related(
            "client"
        )

    def get_serializer_class(self):
        if self.action == "count":
            return SubscriberCountSerializer
        return ProviderSubscriberSerializer

    @action(detail=False, methods=["get"])
    def count(self, request):
        return Response({"count": self.get_queryset().count()})
