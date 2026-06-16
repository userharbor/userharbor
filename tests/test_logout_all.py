import pytest

from userharbor.exceptions import InvalidSessionTokenError


def test_logout_all_removes_all_sessions(userharbor, store, logged_in_user) -> None:
    registered_user, _ = logged_in_user
    latest_session_token = userharbor.login(
        registered_user.username, registered_user.password
    )

    userharbor.logout_all(latest_session_token)

    assert store.users[registered_user.username].session_token_hashes == []


def test_logout_all_removes_sessions_for_session_owner(
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

    userharbor.logout_all(second_session_token)

    assert store.users[first_user.username].session_token_hashes != []
    assert store.users[second_user.username].session_token_hashes == []


def test_logout_all_rejects_invalid_session_token(
    userharbor, store, logged_in_user
) -> None:
    registered_user, _ = logged_in_user
    session_token_hashes = store.users[registered_user.username].session_token_hashes
    assert session_token_hashes is not None
    sessions_before_logout = session_token_hashes.copy()

    with pytest.raises(InvalidSessionTokenError, match="Invalid session token"):
        userharbor.logout_all("wrong-session-token")

    assert (
        store.users[registered_user.username].session_token_hashes
        == sessions_before_logout
    )
