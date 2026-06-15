from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.users.enums import UserRole


class IsFamily(BasePermission):
    """
    Allow access only to authenticated users with role == FAMILY.
    """

    message = "You must be a family account to access this resource."

    def has_permission(self, request: Request, view: APIView) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.FAMILY
        )
