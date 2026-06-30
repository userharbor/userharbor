import pytest

from userharbor.exceptions import (
    InvalidPermissionError,
    InvalidRoleError,
    InvalidSessionTokenError,
    InvalidUsernameError,
    PermissionDeniedError,
    UnknownPermissionError,
    UnknownRoleError,
)


def test_grant_role_assigns_role_to_user(userharbor, register_user) -> None:
    registered_user = register_user()
    userharbor.roles.create("admin")

    userharbor.grant_role(registered_user.username, "admin")
    userharbor.grant_role(registered_user.username, "admin")

    assert userharbor.get_roles(registered_user.username) == {"admin"}


def test_revoke_role_removes_role_from_user(userharbor, register_user) -> None:
    registered_user = register_user()
    userharbor.roles.create("admin")
    userharbor.grant_role(registered_user.username, "admin")

    userharbor.revoke_role(registered_user.username, "admin")
    userharbor.revoke_role(registered_user.username, "admin")

    assert userharbor.get_roles(registered_user.username) == set()


def test_grant_role_rejects_unknown_user(userharbor) -> None:
    userharbor.roles.create("admin")

    with pytest.raises(InvalidUsernameError, match="Unknown username"):
        userharbor.grant_role("missing123", "admin")


def test_grant_role_rejects_invalid_username(userharbor) -> None:
    userharbor.roles.create("admin")

    with pytest.raises(InvalidUsernameError, match="Invalid username"):
        userharbor.grant_role("x", "admin")


def test_grant_role_rejects_invalid_role(userharbor, register_user) -> None:
    registered_user = register_user()

    with pytest.raises(InvalidRoleError, match="Invalid role"):
        userharbor.grant_role(registered_user.username, "Admin")


def test_grant_role_rejects_unknown_role(userharbor, register_user) -> None:
    registered_user = register_user()

    with pytest.raises(UnknownRoleError, match="Unknown role"):
        userharbor.grant_role(registered_user.username, "admin")


def test_get_permissions_returns_permissions_from_user_roles(
    userharbor, register_user
) -> None:
    registered_user = register_user()
    userharbor.roles.create("admin")
    userharbor.roles.create("billing")
    userharbor.permissions.create("users.delete")
    userharbor.permissions.create("invoices.read")
    userharbor.roles.grant_permission("admin", "users.delete")
    userharbor.roles.grant_permission("billing", "invoices.read")
    userharbor.grant_role(registered_user.username, "admin")
    userharbor.grant_role(registered_user.username, "billing")

    assert userharbor.get_permissions(registered_user.username) == {
        "users.delete",
        "invoices.read",
    }


def test_has_role_and_has_permission_return_true_for_allowed_user(
    userharbor, logged_in_user
) -> None:
    registered_user, session_token = logged_in_user
    userharbor.roles.create("admin")
    userharbor.permissions.create("users.delete")
    userharbor.roles.grant_permission("admin", "users.delete")
    userharbor.grant_role(registered_user.username, "admin")

    assert userharbor.has_role(session_token, "admin")
    assert userharbor.has_permission(session_token, "users.delete")


def test_has_role_and_has_permission_return_false_for_denied_user(
    userharbor, logged_in_user
) -> None:
    _, session_token = logged_in_user
    userharbor.roles.create("admin")
    userharbor.permissions.create("users.delete")

    assert not userharbor.has_role(session_token, "admin")
    assert not userharbor.has_permission(session_token, "users.delete")


def test_has_role_and_has_permission_return_false_for_invalid_session(
    userharbor,
) -> None:
    userharbor.roles.create("admin")
    userharbor.permissions.create("users.delete")

    assert not userharbor.has_role("wrong-session-token", "admin")
    assert not userharbor.has_permission("wrong-session-token", "users.delete")


def test_has_permission_rejects_unknown_permission(
    userharbor, logged_in_user
) -> None:
    _, session_token = logged_in_user

    with pytest.raises(UnknownPermissionError, match="Unknown permission"):
        userharbor.has_permission(session_token, "users.delete")


def test_has_role_rejects_unknown_role(userharbor, logged_in_user) -> None:
    _, session_token = logged_in_user

    with pytest.raises(UnknownRoleError, match="Unknown role"):
        userharbor.has_role(session_token, "admin")


def test_has_permission_rejects_invalid_permission(
    userharbor, logged_in_user
) -> None:
    _, session_token = logged_in_user

    with pytest.raises(InvalidPermissionError, match="Invalid permission"):
        userharbor.has_permission(session_token, "delete")


def test_require_role_and_require_permission_return_current_user(
    userharbor, logged_in_user
) -> None:
    registered_user, session_token = logged_in_user
    userharbor.roles.create("admin")
    userharbor.permissions.create("users.delete")
    userharbor.roles.grant_permission("admin", "users.delete")
    userharbor.grant_role(registered_user.username, "admin")

    role_user = userharbor.require_role(session_token, "admin")
    permission_user = userharbor.require_permission(session_token, "users.delete")

    assert role_user.username == registered_user.username
    assert permission_user.username == registered_user.username


def test_require_role_rejects_missing_role(userharbor, logged_in_user) -> None:
    _, session_token = logged_in_user
    userharbor.roles.create("admin")

    with pytest.raises(PermissionDeniedError, match="Permission denied"):
        userharbor.require_role(session_token, "admin")


def test_require_role_rejects_unknown_role(userharbor, logged_in_user) -> None:
    _, session_token = logged_in_user

    with pytest.raises(UnknownRoleError, match="Unknown role"):
        userharbor.require_role(session_token, "admin")


def test_require_permission_rejects_missing_permission(
    userharbor, logged_in_user
) -> None:
    _, session_token = logged_in_user
    userharbor.permissions.create("users.delete")

    with pytest.raises(PermissionDeniedError, match="Permission denied"):
        userharbor.require_permission(session_token, "users.delete")


def test_require_role_rejects_invalid_session(userharbor) -> None:
    userharbor.roles.create("admin")

    with pytest.raises(InvalidSessionTokenError, match="Invalid session token"):
        userharbor.require_role("wrong-session-token", "admin")


def test_require_permission_rejects_session_with_missing_user(
    userharbor, store, logged_in_user
) -> None:
    registered_user, session_token = logged_in_user
    userharbor.permissions.create("users.delete")
    del store.users[registered_user.username]

    with pytest.raises(InvalidSessionTokenError, match="Invalid session token"):
        userharbor.require_permission(session_token, "users.delete")


def test_require_role_rejects_invalid_role(userharbor, logged_in_user) -> None:
    _, session_token = logged_in_user

    with pytest.raises(InvalidRoleError, match="Invalid role"):
        userharbor.require_role(session_token, "Admin")
