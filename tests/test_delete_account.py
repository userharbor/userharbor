import pytest

from userharbor.exceptions import InvalidCredentialsError, InvalidSessionTokenError


def test_delete_account_removes_sessions_and_user(
    userharbor, store, logged_in_user
) -> None:
    registered_user, session_token = logged_in_user

    userharbor.delete_account(
        registered_user.password,
        session_token,
    )

    assert registered_user.username not in store.users


def test_delete_account_removes_session_owner(
    userharbor, store, logged_in_user, register_user
) -> None:
    first_user, _ = logged_in_user
    second_user = register_user(
        username="kasia123",
        email="kasia@example.com",
    )
    userharbor.verify_email(second_user.verification_token)
    second_session_token = userharbor.login(
        second_user.username,
        second_user.password,
    )

    userharbor.delete_account(second_user.password, second_session_token)

    assert first_user.username in store.users
    assert second_user.username not in store.users


def test_delete_account_rejects_invalid_session_token(
    userharbor, store, logged_in_user
) -> None:
    registered_user, _ = logged_in_user
    users_before_delete = store.users.copy()

    with pytest.raises(InvalidSessionTokenError, match="Invalid session token"):
        userharbor.delete_account(
            registered_user.password,
            "wrong-session-token",
        )

    assert store.users == users_before_delete


def test_delete_account_rejects_invalid_password(
    userharbor, store, logged_in_user
) -> None:
    registered_user, session_token = logged_in_user
    users_before_delete = store.users.copy()

    with pytest.raises(InvalidCredentialsError, match="Invalid password"):
        userharbor.delete_account(
            "Wrongpass1!",
            session_token,
        )

    assert store.users == users_before_delete
