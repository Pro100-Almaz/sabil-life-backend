from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.users.enums import UserRole


class HasRole(BasePermission):
    """
    Generic role gate.  Subclass and set ``required_roles`` to a set of
    UserRole values.  Access is granted when the authenticated user holds
    **any** of the listed roles (OR logic).

    MANAGER implicitly satisfies every role except ADMIN — this is handled
    inside ``CustomUser.has_role``, so permission classes don't need to
    special-case it.
    """

    required_roles: set[str] = set()
    message = "You do not have the required role to access this resource."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.has_any_role(*self.required_roles)


class IsFamily(HasRole):
    required_roles = {UserRole.FAMILY}
    message = "You must be a family account to access this resource."


class IsProvider(HasRole):
    required_roles = {UserRole.TUTOR, UserRole.MASTERCLASS}
    message = "You must be a provider (TUTOR or MASTERCLASS) to access this resource."


class IsTutor(HasRole):
    required_roles = {UserRole.TUTOR}
    message = "Only users with the TUTOR role can access this resource."


class IsManager(HasRole):
    required_roles = {UserRole.MANAGER}
    message = "Only managers can access this resource."


class IsAdmin(HasRole):
    required_roles = {UserRole.ADMIN}
    message = "Only admins can access this resource."


class IsManagerOrAdmin(HasRole):
    required_roles = {UserRole.MANAGER, UserRole.ADMIN}
    message = "Only managers or admins can access this resource."

class IsMasterclass(HasRole):
    required_roles = {UserRole.MASTERCLASS}
    message = "Only masterclasses can access this resource."


class IsMasterclassManagerOrAdmin(HasRole):
    required_roles = {UserRole.MASTERCLASS, UserRole.MANAGER, UserRole.ADMIN}
    message = (
        "Only masterclass providers, managers, or admins can manage listings."
    )
