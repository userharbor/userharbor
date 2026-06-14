import pytest

from userharbor.exceptions import InvalidPasswordError, InvalidSessionTokenError


def test_delete_account_removes_sessions_and_user(
    userharbor, store, logged_in_user
) -> None:
    registered_user, session_token = logged_in_user

    userharbor.delete_account(
        registered_user.username,
        registered_user.password,
        session_token,
    )

    assert registered_user.username not in store.users


def test_delete_account_rejects_invalid_session_token(
    userharbor, store, logged_in_user
) -> None:
    registered_user, _ = logged_in_user
    users_before_delete = store.users.copy()

    with pytest.raises(InvalidSessionTokenError, match="Invalid session token"):
        userharbor.delete_account(
            registered_user.username,
            registered_user.password,
            "wrong-session-token",
        )

    assert store.users == users_before_delete


def test_delete_account_rejects_invalid_password(
    userharbor, store, logged_in_user
) -> None:
    registered_user, session_token = logged_in_user
    users_before_delete = store.users.copy()

    with pytest.raises(InvalidPasswordError, match="Invalid password"):
        userharbor.delete_account(
            registered_user.username,
            "Wrongpass1!",
            session_token,
        )

    assert store.users == users_before_delete
