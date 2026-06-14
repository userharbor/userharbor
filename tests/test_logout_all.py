import pytest

from userharbor.exceptions import InvalidSessionTokenError


def test_logout_all_removes_all_sessions(userharbor, store, logged_in_user) -> None:
    registered_user, _ = logged_in_user
    latest_session_token = userharbor.login(
        registered_user.username, registered_user.password
    )

    userharbor.logout_all(registered_user.username, latest_session_token)

    assert store.users[registered_user.username].session_token_hashes == []


def test_logout_all_rejects_invalid_session_token(
    userharbor, store, logged_in_user
) -> None:
    registered_user, _ = logged_in_user
    session_token_hashes = store.users[registered_user.username].session_token_hashes
    assert session_token_hashes is not None
    sessions_before_logout = session_token_hashes.copy()

    with pytest.raises(InvalidSessionTokenError, match="Invalid session token"):
        userharbor.logout_all(registered_user.username, "wrong-session-token")

    assert (
        store.users[registered_user.username].session_token_hashes
        == sessions_before_logout
    )
