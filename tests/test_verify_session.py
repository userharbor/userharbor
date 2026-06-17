from datetime import timedelta

from userharbor.utils import utcnow


def test_verify_session_accepts_valid_session_token(userharbor, logged_in_user) -> None:
    _, session_token = logged_in_user

    assert userharbor.verify_session(session_token)


def test_verify_session_rejects_invalid_session_token(
    userharbor, logged_in_user
) -> None:
    _ = logged_in_user

    assert not userharbor.verify_session("wrong-session-token")


def test_verify_session_removes_expired_session(
    userharbor, store, logged_in_user
) -> None:
    registered_user, session_token = logged_in_user
    session_token_hash = store.users[registered_user.username].session_token_hashes[-1]
    store.sessions[session_token_hash].expires_at = utcnow() - timedelta(days=1)

    assert not userharbor.verify_session(session_token)
    assert store.users[registered_user.username].session_token_hashes == []
    assert store.get_session(session_token_hash) is None
