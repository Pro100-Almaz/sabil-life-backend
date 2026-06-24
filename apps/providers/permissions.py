from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsListingOwner(BasePermission):
    message = "You do not own this listing."

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        return bool(obj.owner_id == request.user.id)
