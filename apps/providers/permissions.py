from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsProvider(BasePermission):
    """
    Allow access only to authenticated users whose role is TUTOR or MASTERCLASS.

    ADMIN users return False — admins manage providers via the Django admin panel
    at /admin-panel/, not through the provider self-service API.
    """

    message = "You must be a provider (TUTOR or MASTERCLASS) to access this resource."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user and request.user.is_authenticated and request.user.is_provider
        )


class IsTutor(BasePermission):
    message = "Only users with the TUTOR role can access this resource."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "TUTOR"
        )


class IsListingOwner(BasePermission):
    """
    Object-level permission: only the owner of the listing may act on it.

    This is a belt-and-suspenders guard; the primary enforcement is
    get_queryset() filtering to owner=request.user in ProviderListingViewSet,
    which means unauthorised access returns 404 rather than 403.  This
    permission fires for the object-level check on retrieve/update/destroy.
    """

    message = "You do not own this listing."

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        return bool(obj.owner_id == request.user.id)
