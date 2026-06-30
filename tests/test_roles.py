import pytest

from userharbor.exceptions import (
    InvalidPermissionError,
    InvalidRoleError,
    PermissionAlreadyExistsError,
    RoleAlreadyExistsError,
    UnknownPermissionError,
    UnknownRoleError,
)


def test_roles_create_list_and_delete(userharbor) -> None:
    userharbor.roles.create("admin")
    userharbor.roles.create("support-agent")

    assert userharbor.roles.list() == {"admin", "support-agent"}

    userharbor.roles.delete("admin")

    assert userharbor.roles.list() == {"support-agent"}


def test_roles_create_rejects_invalid_role(userharbor) -> None:
    with pytest.raises(InvalidRoleError, match="Invalid role"):
        userharbor.roles.create("Admin")


def test_roles_create_rejects_existing_role(userharbor) -> None:
    userharbor.roles.create("admin")

    with pytest.raises(RoleAlreadyExistsError, match="Role already exists"):
        userharbor.roles.create("admin")


def test_roles_delete_rejects_unknown_role(userharbor) -> None:
    with pytest.raises(UnknownRoleError, match="Unknown role"):
        userharbor.roles.delete("admin")


def test_roles_grant_and_revoke_permission(userharbor) -> None:
    userharbor.roles.create("admin")
    userharbor.permissions.create("users.delete")

    userharbor.roles.grant_permission("admin", "users.delete")
    userharbor.roles.grant_permission("admin", "users.delete")

    assert userharbor.roles.permissions("admin") == {"users.delete"}

    userharbor.roles.revoke_permission("admin", "users.delete")
    userharbor.roles.revoke_permission("admin", "users.delete")

    assert userharbor.roles.permissions("admin") == set()


def test_roles_grant_permission_rejects_invalid_permission(userharbor) -> None:
    userharbor.roles.create("admin")

    with pytest.raises(InvalidPermissionError, match="Invalid permission"):
        userharbor.roles.grant_permission("admin", "delete")


def test_roles_grant_permission_rejects_unknown_role(userharbor) -> None:
    userharbor.permissions.create("users.delete")

    with pytest.raises(UnknownRoleError, match="Unknown role"):
        userharbor.roles.grant_permission("admin", "users.delete")


def test_roles_grant_permission_rejects_unknown_permission(userharbor) -> None:
    userharbor.roles.create("admin")

    with pytest.raises(UnknownPermissionError, match="Unknown permission"):
        userharbor.roles.grant_permission("admin", "users.delete")


def test_roles_delete_removes_role_from_users_and_permissions(
    userharbor, store, register_user
) -> None:
    registered_user = register_user()
    userharbor.roles.create("admin")
    userharbor.permissions.create("users.delete")
    userharbor.roles.grant_permission("admin", "users.delete")
    userharbor.grant_role(registered_user.username, "admin")

    userharbor.roles.delete("admin")

    assert userharbor.get_roles(registered_user.username) == set()
    assert "admin" not in store.role_permissions


def test_permissions_create_list_and_delete(userharbor) -> None:
    userharbor.permissions.create("users.read")
    userharbor.permissions.create("users.delete")

    assert userharbor.permissions.list() == {"users.read", "users.delete"}

    userharbor.permissions.delete("users.delete")

    assert userharbor.permissions.list() == {"users.read"}


def test_permissions_create_rejects_invalid_permission(userharbor) -> None:
    with pytest.raises(InvalidPermissionError, match="Invalid permission"):
        userharbor.permissions.create("delete")


def test_permissions_create_rejects_existing_permission(userharbor) -> None:
    userharbor.permissions.create("users.delete")

    with pytest.raises(
        PermissionAlreadyExistsError, match="Permission already exists"
    ):
        userharbor.permissions.create("users.delete")


def test_permissions_delete_rejects_unknown_permission(userharbor) -> None:
    with pytest.raises(UnknownPermissionError, match="Unknown permission"):
        userharbor.permissions.delete("users.delete")


def test_permissions_delete_removes_permission_from_roles(userharbor) -> None:
    userharbor.roles.create("admin")
    userharbor.permissions.create("users.delete")
    userharbor.roles.grant_permission("admin", "users.delete")

    userharbor.permissions.delete("users.delete")

    assert userharbor.roles.permissions("admin") == set()
