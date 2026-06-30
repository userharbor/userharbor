from typing import Generic

from .exceptions import (
    InvalidPermissionError,
    InvalidRoleError,
    PermissionAlreadyExistsError,
    RoleAlreadyExistsError,
    UnknownPermissionError,
    UnknownRoleError,
)
from .interfaces import UserStore, UserT
from .validations import is_permission_valid, is_role_valid


class RoleManager(Generic[UserT]):
    def __init__(self, store: UserStore[UserT]) -> None:
        self._store = store

    def create(self, role: str) -> None:
        _validate_role(role)
        if self._store.role_exists(role):
            raise RoleAlreadyExistsError("Role already exists")
        self._store.create_role(role)

    def delete(self, role: str) -> None:
        _validate_role(role)
        self._require_role(role)
        self._store.delete_role(role)

    def list(self) -> set[str]:
        return self._store.list_roles()

    def grant_permission(self, role: str, permission: str) -> None:
        _validate_role(role)
        _validate_permission(permission)
        self._require_role(role)
        _require_permission(self._store, permission)
        self._store.grant_permission_to_role(role, permission)

    def revoke_permission(self, role: str, permission: str) -> None:
        _validate_role(role)
        _validate_permission(permission)
        self._require_role(role)
        _require_permission(self._store, permission)
        self._store.revoke_permission_from_role(role, permission)

    def permissions(self, role: str) -> set[str]:
        _validate_role(role)
        self._require_role(role)
        return self._store.get_role_permissions(role)

    def _require_role(self, role: str) -> None:
        if not self._store.role_exists(role):
            raise UnknownRoleError("Unknown role")


class PermissionManager(Generic[UserT]):
    def __init__(self, store: UserStore[UserT]) -> None:
        self._store = store

    def create(self, permission: str) -> None:
        _validate_permission(permission)
        if self._store.permission_exists(permission):
            raise PermissionAlreadyExistsError("Permission already exists")
        self._store.create_permission(permission)

    def delete(self, permission: str) -> None:
        _validate_permission(permission)
        _require_permission(self._store, permission)
        self._store.delete_permission(permission)

    def list(self) -> set[str]:
        return self._store.list_permissions()


def _validate_role(role: str) -> None:
    if not is_role_valid(role):
        raise InvalidRoleError("Invalid role")


def _validate_permission(permission: str) -> None:
    if not is_permission_valid(permission):
        raise InvalidPermissionError("Invalid permission")


def _require_permission(store: UserStore[UserT], permission: str) -> None:
    if not store.permission_exists(permission):
        raise UnknownPermissionError("Unknown permission")
