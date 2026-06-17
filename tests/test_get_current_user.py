from datetime import timedelta

import pytest

from userharbor.exceptions import InvalidSessionTokenError
from userharbor.utils import utcnow


def test_get_current_user_returns_session_owner(userharbor, logged_in_user) -> None:
    registered_user, session_token = logged_in_user

    current_user = userharbor.get_current_user(session_token)

    assert current_user.username == registered_user.username
    assert current_user.email == registered_user.email
    assert current_user.verified


def test_get_current_user_rejects_invalid_session_token(
    userharbor, store, logged_in_user
) -> None:
    registered_user, _ = logged_in_user
    session_token_hashes = store.users[registered_user.username].session_token_hashes
    assert session_token_hashes is not None
    sessions_before_get_current_user = session_token_hashes.copy()

    with pytest.raises(InvalidSessionTokenError, match="Invalid session token"):
        userharbor.get_current_user("wrong-session-token")

    assert (
        store.users[registered_user.username].session_token_hashes
        == sessions_before_get_current_user
    )


def test_get_current_user_removes_expired_session(
    userharbor, store, logged_in_user
) -> None:
    registered_user, session_token = logged_in_user
    session_token_hash = store.users[registered_user.username].session_token_hashes[-1]
    store.sessions[session_token_hash].expires_at = utcnow() - timedelta(days=1)

    with pytest.raises(InvalidSessionTokenError, match="Session token expired"):
        userharbor.get_current_user(session_token)

    assert store.users[registered_user.username].session_token_hashes == []
    assert store.get_session(session_token_hash) is None
