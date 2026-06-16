import pytest

from userharbor.exceptions import InvalidSessionTokenError


def test_logout_removes_valid_session(userharbor, store, logged_in_user) -> None:
    registered_user, session_token = logged_in_user

    userharbor.logout(session_token)

    assert store.users[registered_user.username].session_token_hashes == []


def test_logout_rejects_invalid_session_token(
    userharbor, store, logged_in_user
) -> None:
    registered_user, _ = logged_in_user
    session_token_hashes = store.users[registered_user.username].session_token_hashes
    assert session_token_hashes is not None
    sessions_before_logout = session_token_hashes.copy()

    with pytest.raises(InvalidSessionTokenError, match="Invalid session token"):
        userharbor.logout("wrong-session-token")

    assert (
        store.users[registered_user.username].session_token_hashes
        == sessions_before_logout
    )
